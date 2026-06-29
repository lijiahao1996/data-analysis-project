# -*- coding: utf-8 -*-
"""
数据本地化转换脚本
将巴西 Olist 电商数据转换为中国电商平台数据
用法: python scripts/rebrand_data.py
"""
import pandas as pd
from pathlib import Path
import hashlib
import random
import re

# ============================================================
# 映射字典
# ============================================================

STATE_MAP = {
    'SP': '上海', 'RJ': '北京', 'MG': '广东', 'RS': '浙江',
    'PR': '江苏', 'SC': '福建', 'BA': '四川', 'PE': '湖北',
    'CE': '山东', 'GO': '河南', 'PA': '辽宁', 'MA': '安徽',
    'ES': '湖南', 'PB': '陕西', 'AM': '云南', 'MT': '贵州',
    'RN': '广西', 'AL': '河北', 'PI': '江西', 'DF': '天津',
    'SE': '重庆', 'RO': '吉林', 'TO': '黑龙江', 'MS': '海南',
    'AC': '甘肃', 'AP': '内蒙古', 'RR': '新疆', 'XX': '未知'
}

# 每个省份对应的省会/主要城市（用于不在 CITY_MAP 中的城市兜底）
PROVINCE_CAPITAL = {
    '上海': '上海', '北京': '北京', '广东': '广州', '浙江': '杭州',
    '江苏': '南京', '福建': '福州', '四川': '成都', '湖北': '武汉',
    '山东': '济南', '河南': '郑州', '辽宁': '沈阳', '安徽': '合肥',
    '湖南': '长沙', '陕西': '西安', '云南': '昆明', '贵州': '贵阳',
    '广西': '南宁', '河北': '石家庄', '江西': '南昌', '天津': '天津',
    '重庆': '重庆', '吉林': '长春', '黑龙江': '哈尔滨', '海南': '海口',
    '甘肃': '兰州', '内蒙古': '呼和浩特', '新疆': '乌鲁木齐', '未知': '未知'
}

CITY_MAP = {
    'sao paulo': '上海', 'rio de janeiro': '北京', 'belo horizonte': '广州',
    'brasilia': '天津', 'curitiba': '南京', 'porto alegre': '杭州',
    'salvador': '成都', 'recife': '武汉', 'fortaleza': '济南',
    'campinas': '苏州', 'santos': '宁波', 'sao bernardo do campo': '无锡',
    'guarulhos': '嘉定', 'osasco': '松江', 'ribeirao preto': '常州',
    'goiania': '郑州', 'manaus': '昆明', 'cuiaba': '贵阳',
    'belém': '沈阳', 'nova iguacu': '朝阳', 'sao goncalo': '丰台',
    'niteroi': '海淀', 'duque de caxias': '通州', 'feira de santana': '绵阳',
    'joinville': '厦门', 'londrina': '南通', 'juiz de fora': '东莞',
    'florianopolis': '福州', 'natal': '南宁', 'aracaju': '石家庄',
    'campo grande': '海口', 'teresina': '南昌', 'macapa': '呼和浩特',
    'boa vista': '乌鲁木齐', 'porto velho': '长春', 'rio branco': '兰州',
    'palmas': '哈尔滨', 'vitoria': '长沙', 'sao jose dos campos': '佛山',
    'jundiai': '温州', 'sorocaba': '绍兴', 'petropolis': '昌平',
    'maringa': '扬州', 'uberlandia': '珠海', 'contagem': '深圳',
    'novo hamburgo': '嘉兴', 'sao jose': '青岛', 'betim': '中山',
    'caxias do sul': '金华', 'piracicaba': '镇江', 'blumenau': '泉州',
    'sao carlos': '芜湖', 'santa maria': '台州', 'pelotas': '湖州',
    'marilia': '徐州', 'americana': '无锡', 'taubate': '嘉兴',
    'sao jose do rio preto': '盐城', 'paulista': '烟台', 'maua': '金山',
    'sao vicente': '张家港', 'cariacica': '株洲', 'caruaru': '宜昌',
    'montes claros': '韶关', 'uberaba': '惠州', 'cascavel': '漳州',
    'franca': '洛阳', 'guarujá': '日照',
}

CATEGORY_MAP = {
    'beleza_saude': '美妆个护',
    'relogios_presentes': '钟表礼品',
    'cama_mesa_banho': '家纺布艺',
    'esporte_lazer': '运动户外',
    'informatica_acessorios': '电脑配件',
    'moveis_decoracao': '家居装饰',
    'utilidades_domesticas': '家居日用',
    'cool_stuff': '创意潮品',
    'automotivo': '汽车用品',
    'ferramentas_jardim': '五金园艺',
    'perfumaria': '香水香氛',
    'bebes': '母婴用品',
    'eletronicos': '数码电子',
    'papelaria': '文具办公',
    'fashion_bolsas_e_acessorios': '箱包配饰',
    'pet_shop': '宠物用品',
    'moveis_escritorio': '办公家具',
    'market_place': '综合特卖',
    'construcao_ferramentas_construcao': '建材工具',
    'eletrodomesticos': '家用电器',
    'instrumentos_musicais': '乐器音响',
    'malas_acessorios': '旅行箱包',
    'construcao_ferramentas_iluminacao': '灯具照明',
    'climatizacao': '空调暖通',
    'moveis_cozinha_area_de_servico_jantar_e_jardim': '厨卫餐饮',
    'alimentos': '食品生鲜',
    'construcao_ferramentas_jardim': '园艺工具',
    'fashion_roupa_masculina': '男装',
    'fashion_roupa_feminina': '女装',
    'livros_tecnicos': '科技图书',
    'telefonia': '手机通讯',
    'fashion_calcados': '鞋靴',
    'industria_comercio_e_negocios': '工业商务',
    'brinquedos': '玩具',
    'house': '居家生活',
    'livros_interesse_geral': '大众图书',
    'escritorio': '办公用品',
    'artes': '艺术收藏',
    'construcao_ferramentas_seguranca': '安防设备',
    'fashion_underwear_e_moda_praia': '内衣泳装',
    'sinalizacao_e_seguranca': '标识安防',
    'pcs': '电脑整机',
    'artigos_de_natal': '节日用品',
    'fashion_esporte_e_fitness': '运动服饰',
    'cine_foto': '摄影器材',
    'dvds_blu_ray': '影视光盘',
    'musica': '音乐制品',
    'la_cuisine': '厨房用品',
    'fashion_roupa_infanto_juvenil': '童装',
    'seguros_e_servicos': '保险服务',
    'agro_industria_e_comercio': '农工商品',
    'artes_e_artesanato': '手工艺品',
    'fraldas_higiene': '纸尿裤洗护',
    'fashion_roupa_bebe': '婴儿服饰',
    'moveis_sala': '客厅家具',
    'construcao_ferramentas_ferramentas': '手动工具',
    'livros_importados': '进口图书',
    'bebidas': '酒水饮料',
    'audio': '音响设备',
    'portateis_casa_forno_e_cafe': '小厨电',
    'portateis_cozinha_e_preparadores_de_alimentos': '厨房电器',
    'cds_dvds_musicais': '音乐光盘',
    'flores': '鲜花绿植',
    'pc_gamer': '游戏电脑',
    'tablets_impressao_e_acessorios': '平板打印',
    'moveis_colchao_e_estofado': '床垫沙发',
    'moveis_quarto': '卧室家具',
    'consoles': '游戏主机',
    'videos': '游戏软件',
    'construcao_ferramentas_medicao': '测量工具',
    'televisores': '电视机',
    'home_confort_2': '家居舒适',
    'home_confort': '家居舒适',
    'casa_conforto': '家居舒适',
    'artigos_de_festas': '派对用品',
    'telefonia_fixa': '固定电话',
    'eletroportateis': '小家电',
}

PAYMENT_MAP = {
    'credit_card': '信用卡',
    'boleto': '花呗',
    'voucher': '余额支付',
    'debit_card': '借记卡',
    'not_defined': '其他'
}

# 卖家名称生成素材
PROVINCES = ['北京', '上海', '广东', '浙江', '江苏', '四川', '湖北', '山东']
SHOP_TYPES = ['旗舰店', '专营店', '官方店', '直营店', '品牌店', '优品店']
# 品类词（用于卖家名称）
SHOP_CATEGORIES = [
    '美妆', '数码', '家居', '服饰', '食品', '母婴', '运动', '家电',
    '箱包', '珠宝', '办公', '玩具', '宠物', '图书', '鞋靴', '生鲜'
]

# 评论模板
POSITIVE_TEMPLATES = [
    "质量很好，物流也快，很满意！",
    "包装完好，商品和描述一致，好评。",
    "性价比很高，推荐购买。",
    "第二次回购了，品质确实不错。",
    "物流很快，两天就到了，商品也很好用。",
    "颜色跟图片一样，没有色差，喜欢。",
    "做工精细，手感很好，值得购买。",
    "比预期好很多，功能齐全，操作方便。",
    "朋友推荐来的，果然没让我失望。",
    "收到货很惊喜，比想象中好很多！",
    "用了几天感觉很好，质量过关。",
    "快递很给力，包装也很用心。",
    "这个价格买到这个质量，赚到了！",
    "店家服务态度很好，有问必答。",
    "正品无疑，跟实体店一样，便宜好多。",
    "发货速度快，商品质量不错，满意。",
    "给家里买的，家人很喜欢。",
    "老客户了，一如既往的好。",
    "非常棒的一次购物体验，五星好评！",
    "安装方便，使用简单，强烈推荐。",
]

NEUTRAL_TEMPLATES = [
    "一般般吧，没有想象中好，但也能用。",
    "质量还行，就是物流有点慢。",
    "商品本身没问题，包装稍微简陋了点。",
    "凑合用吧，性价比一般。",
    "还可以，跟我之前买的差不多。",
    "收到了，总体来说中规中矩。",
    "功能正常，外观有点小瑕疵。",
    "等了几天才到，东西还行。",
    "基本符合预期，没有什么特别的。",
    "马马虎虎吧，不好也不差。",
    "质量一般，胜在价格便宜。",
    "能用，但是没有太大惊喜。",
    "物流速度一般，商品还行。",
    "和描述基本一致，没什么大问题。",
    "普通水平，随便用用可以。",
]

NEGATIVE_TEMPLATES = [
    "物流太慢了，等了一个多星期才到。",
    "质量一般，和图片差距较大。",
    "包装破损，联系客服也没解决。",
    "收到的跟描述的完全不一样，差评。",
    "用了一次就坏了，质量太差。",
    "尺寸不对，退换货太麻烦。",
    "客服态度很差，问什么都不理。",
    "这个价格真的不值，质量太差了。",
    "发了个次品过来，浪费时间。",
    "快递很慢，而且包装特别简陋，商品有划痕。",
    "与预期差距很大，不推荐购买。",
    "味道很大，放了好几天还是有味。",
    "做工粗糙，线头到处都是。",
    "刚收到就有问题，申请退货了。",
    "跟图片完全不符，颜色差太多了。",
    "太差了，根本没法用，直接扔了。",
    "等了半个月才收到，催了无数次。",
    "商品有明显瑕疵，品控太差。",
    "实物比图片小很多，尺寸标注有误。",
    "售后服务形同虚设，打电话永远占线。",
]


def _map_city(city: str, state: str) -> str:
    """将巴西城市映射为中国城市"""
    city_lower = str(city).strip().lower()
    if city_lower in CITY_MAP:
        return CITY_MAP[city_lower]
    # 兜底：映射到省份省会
    cn_state = STATE_MAP.get(state, '未知')
    return PROVINCE_CAPITAL.get(cn_state, '未知')


def _map_state(state: str) -> str:
    return STATE_MAP.get(state, '未知')


def _generate_zip() -> str:
    """生成6位中国邮编格式"""
    return f"{random.randint(100000, 999999)}"


def _generate_seller_name(seller_id: str) -> str:
    """基于 seller_id 哈希生成固定中文名"""
    h = int(hashlib.md5(str(seller_id).encode()).hexdigest(), 16)
    province = PROVINCES[h % len(PROVINCES)]
    category = SHOP_CATEGORIES[(h // len(PROVINCES)) % len(SHOP_CATEGORIES)]
    shop_type = SHOP_TYPES[(h // (len(PROVINCES) * len(SHOP_CATEGORIES))) % len(SHOP_TYPES)]
    return f"{province}{category}{shop_type}"


def _generate_review(score: int, original_msg: str) -> str:
    """按评分生成中文评论，保持空评论为空"""
    if pd.isna(original_msg) or str(original_msg).strip() == '':
        return ''
    if score >= 4:
        return random.choice(POSITIVE_TEMPLATES)
    elif score == 3:
        return random.choice(NEUTRAL_TEMPLATES)
    else:
        return random.choice(NEGATIVE_TEMPLATES)


# ============================================================
# 各表转换函数
# ============================================================

def rebrand_customers(df: pd.DataFrame) -> pd.DataFrame:
    """转换客户地址数据"""
    df = df.copy()
    df['customer_city'] = df.apply(
        lambda row: _map_city(row['customer_city'], row['customer_state']), axis=1
    )
    df['customer_state'] = df['customer_state'].map(_map_state)
    df['customer_zip_code_prefix'] = df['customer_zip_code_prefix'].apply(
        lambda x: _generate_zip()
    )
    return df


def rebrand_products(df: pd.DataFrame) -> pd.DataFrame:
    """转换品类名称"""
    df = df.copy()
    df['product_category_name'] = df['product_category_name'].map(
        lambda x: CATEGORY_MAP.get(x, '其他') if pd.notna(x) else x
    )
    return df


def rebrand_orders(df: pd.DataFrame) -> pd.DataFrame:
    """订单表无需大改，保持原样"""
    return df.copy()


def rebrand_order_items(df: pd.DataFrame) -> pd.DataFrame:
    """订单明细表无需大改"""
    return df.copy()


def rebrand_payments(df: pd.DataFrame) -> pd.DataFrame:
    """转换支付方式"""
    df = df.copy()
    df['payment_type'] = df['payment_type'].map(
        lambda x: PAYMENT_MAP.get(x, x) if pd.notna(x) else x
    )
    return df


def rebrand_reviews(df: pd.DataFrame) -> pd.DataFrame:
    """生成中文评论"""
    df = df.copy()
    # 设置随机种子保证可重复性
    random.seed(42)
    df['review_comment_title'] = ''
    df['review_comment_message'] = df.apply(
        lambda row: _generate_review(row['review_score'], row['review_comment_message']),
        axis=1
    )
    return df


def rebrand_geolocation(df: pd.DataFrame) -> pd.DataFrame:
    """转换地理位置数据（邮编保持原值不变）"""
    df = df.copy()
    df['geolocation_city'] = df.apply(
        lambda row: _map_city(row['geolocation_city'], row['geolocation_state']), axis=1
    )
    df['geolocation_state'] = df['geolocation_state'].map(_map_state)
    return df


def rebrand_sellers(df: pd.DataFrame) -> pd.DataFrame:
    """生成中文卖家名，新增 seller_name 列"""
    df = df.copy()
    df['seller_city'] = df.apply(
        lambda row: _map_city(row['seller_city'], row['seller_state']), axis=1
    )
    df['seller_state'] = df['seller_state'].map(_map_state)
    df['seller_zip_code_prefix'] = df['seller_zip_code_prefix'].apply(
        lambda x: _generate_zip()
    )
    df['seller_name'] = df['seller_id'].apply(_generate_seller_name)
    return df


def rebrand_category_translation(df: pd.DataFrame) -> pd.DataFrame:
    """转换品类翻译表"""
    df = df.copy()
    df['product_category_name'] = df['product_category_name'].map(
        lambda x: CATEGORY_MAP.get(x, '其他') if pd.notna(x) else x
    )
    # english 列也替换为中文（两列都展示中文）
    df['product_category_name_english'] = df['product_category_name'].copy()
    return df


# ============================================================
# 主函数
# ============================================================

def main():
    random.seed(42)

    raw_dir = Path(__file__).parent.parent / 'data' / 'raw'
    out_dir = Path(__file__).parent.parent / 'data' / 'rebranded'
    out_dir.mkdir(exist_ok=True)

    # CSV 文件与处理函数映射
    tasks = {
        'olist_customers_dataset.csv': rebrand_customers,
        'olist_products_dataset.csv': rebrand_products,
        'olist_orders_dataset.csv': rebrand_orders,
        'olist_order_items_dataset.csv': rebrand_order_items,
        'olist_order_payments_dataset.csv': rebrand_payments,
        'olist_order_reviews_dataset.csv': rebrand_reviews,
        'olist_sellers_dataset.csv': rebrand_sellers,
        'olist_geolocation_dataset.csv': rebrand_geolocation,
        'product_category_name_translation.csv': rebrand_category_translation,
    }

    for filename, func in tasks.items():
        src = raw_dir / filename
        if not src.exists():
            print(f"[跳过] {filename} 不存在")
            continue

        # geolocation 表约100万行，分块处理避免内存溢出
        if filename == 'olist_geolocation_dataset.csv':
            print(f"[处理] {filename} (分块处理, chunksize=50000) ...")
            dst = out_dir / filename
            first_chunk = True
            total_rows = 0
            for chunk in pd.read_csv(src, encoding='utf-8', chunksize=50000):
                chunk_out = func(chunk)
                chunk_out.to_csv(
                    dst, index=False, encoding='utf-8-sig',
                    mode='w' if first_chunk else 'a',
                    header=first_chunk
                )
                first_chunk = False
                total_rows += len(chunk_out)
                print(f"  已处理 {total_rows} 行...")
            print(f"  -> 已保存至 {dst}  ({total_rows} 行)")
        else:
            print(f"[处理] {filename} ...")
            df = pd.read_csv(src, encoding='utf-8')
            df_out = func(df)
            dst = out_dir / filename
            df_out.to_csv(dst, index=False, encoding='utf-8-sig')
            print(f"  -> 已保存至 {dst}  ({len(df_out)} 行)")

    print("\n全部转换完成！输出目录:", out_dir)


if __name__ == '__main__':
    main()
