
table_prompt_dict = {}
table_prompt_dict['table_haiku-20240307v1-0_20240407063835']="""
Event：存储的是一家药企的举办市场活动/会议的信息
- name: trty_name, datatype: VARCHAR, comment: 岗位名称
  annotataion:
- name: event_name, datatype: VARCHAR, comment: 活动名称
  annotataion:
- name: event_date, datatype: DATE, comment: 活动时间
  annotataion:
- name: brand, datatype: VARCHAR, comment: 产品
  annotataion: 示例数据，Forxiga 中文名称是安达唐, Tagrisso,Breztri Aero
- name: event_city, datatype: VARCHAR, comment: 活动城市
  annotataion:
- name: event_type, datatype: VARCHAR, comment: 活动类型
  annotataion:
- name: event_status, datatype: VARCHAR, comment: 活动状态
  annotataion: 示例数据，Event Approved for Closing,Event Blocked,Event Cancelled,Event Rejected,Under Rework for Closing,Available for Closing,New,Under Rework,Event Submitted for Closing,Event Submitted
 
internal_sales: 是内部销量表(药品在内部代理和销售大区的销售数据), 存储销售岗位名称、产品、部门、买方所在省、买方所在区域、销售金额等信息, 如果涉及销售区域和买家可以在这里查询。
- name: sales_date, datatype: DATE, comment: 销售日期
  annotataion:
- name: trty_name, datatype: VARCHAR, comment: 销售岗位名称
  annotataion:
- name: brand, datatype: VARCHAR, comment: 产品
  annotataion: 示例数据为,Forxiga(中文名称安达唐)，Tagrisso(中文名称泰瑞沙)，Breztri Aero(中文名称倍择瑞)
- name: bu, datatype: VARCHAR, comment: 销售部门
  annotataion: 示例数据为,RI&B, RGI,OBU,EC,Eagle,CVRM,CHC,BBU_County
- name: sub_bu, datatype: VARCHAR, comment: 销售子部门
  annotataion: 示例数据为,LC,CHC,BBU_County,IPT,GNR,OBU_County,EC
- name: province_name, datatype: VARCHAR, comment: 买方所在省, 值是中国所有省份,如广东
  annotataion:
- name: area_name, datatype: VARCHAR, comment: 买方所在区
  annotataion: 示例数据为,东部地区,中部地区,北部地区,南部地区,西部地区
- name: region_name, datatype: VARCHAR, comment: 销售大区
  annotataion:
- name: region_center_name, datatype: VARCHAR, comment: 销售大区中心
  annotataion:
- name: inst_name, datatype: VARCHAR, comment: 买方名称,值大多是各类购买药品的医院/诊所名称
  annotataion:
- name: sales_val, datatype: DECIMAL, comment: 销售金额
  annotataion:
- name: target_val, datatype: DECIMAL, comment: 目标销售金额
  annotataion:
 
external_sales: 是外部销量表(药品在市场上销售的数据), 存储销量来源、市场、产品、销售日期、销售金额等字段, 如果涉及市场排名可以在这里查询。存储的是多家药企的外部销售数据, 一个药企可能销售多种药, 每种药每段时间在市场上销量为一行数据。
 
- name: source, datatype: VARCHAR, comment: 数据来源, 只有'aia','ims'两种值
  annotataion:
- name: market, datatype: VARCHAR, comment: 市场
  annotataion:
- name: manufacturer, datatype: VARCHAR, comment:
  annotataion:
- name: brand, datatype: VARCHAR, comment: 产品
  annotataion:
- name: is_az, datatype: VARCHAR, comment: 是否是AZ的产品
  annotataion: 数值只有:Y或者N
- name: sales_date, datatype: DATE, comment: 销售日期
  annotataion: 日期的格式是2023-01-01
- name: sales_val, datatype: DECIMAL, comment: 销售金额, 数据类型是(numeric)
  annotataion:
 
listed_brand: 存储的是药企的客户每次来采购药品的数据
 
- name: inst_name, datatype: VARCHAR, comment: 买方名称
  annotataion:
- name: list_date, datatype: DATE, comment: 采购时间
  annotataion: 示例时间是，2023-02-01
- name: brand, datatype: VARCHAR, comment: 产品
  annotataion: 示例数据包括Forxiga,Tagrisso,Breztri Aerok
"""

table_prompt_dict['table_sonnet-20240229v1-0_20240407063835']="""
CREATE TABLE zenmakeovermatch.account (
    id bigint ENCODE zstd
    distkey

        country_code character varying(64) ENCODE zstd,
        country_name character varying(64) ENCODE zstd,
        region_code character varying(64) ENCODE zstd,
        region_name character varying(64) ENCODE zstd,
        city character varying(64) ENCODE zstd,
        time_zone character varying(64) ENCODE zstd,
        platform integer ENCODE zstd,
        device_id character varying(64) ENCODE zstd,
        created_at timestamp without time zone ENCODE zstd,
        updated_at timestamp without time zone ENCODE zstd,
        old_device_id character varying(64) ENCODE zstd,
        facebook_id character varying(64) ENCODE zstd,
        facebook_name character varying(64) ENCODE zstd,
        facebook_email character varying(64) ENCODE zstd,
        migrated_from character varying(64) ENCODE zstd,
        erased_by character varying(64) ENCODE zstd,
        group_ids character varying(64) ENCODE zstd,
        id_string character varying(65535) ENCODE lzo,
        updated_at_string character varying(65535) ENCODE lzo,
        platform_string character varying(65535) ENCODE lzo,
        created_at_string character varying(65535) ENCODE lzo
) DISTSTYLE KEY
SORTKEY
    (updated_at);

CREATE TABLE zenmakeovermatch.common_game_event (
    player_id bigint ENCODE zstd
    distkey
,
        player_type character varying(32) ENCODE zstd,
        player_name character varying(128) ENCODE zstd,
        player_email character varying(128) ENCODE zstd,
        facebook_id character varying(32) ENCODE zstd,
        facebook_email character varying(128) ENCODE zstd,
        facebook_name character varying(128) ENCODE zstd,
        platform character varying(16) ENCODE zstd,
        revenue_usd_cents bigint ENCODE zstd,
        member boolean ENCODE zstd,
        member_age bigint ENCODE zstd,
        member_time bigint ENCODE zstd,
        environment character varying(16) ENCODE zstd,
        client_version character varying(32) ENCODE zstd,
        resource_version character varying(32) ENCODE zstd,
        installed_at timestamp without time zone ENCODE zstd,
        created_at timestamp without time zone ENCODE zstd,
        adjust_id character varying(64) ENCODE zstd,
        adid character varying(64) ENCODE zstd,
        idfa character varying(64) ENCODE zstd,
        device_id character varying(64) ENCODE zstd,
        device_os_name character varying(64) ENCODE zstd,
        device_os_version character varying(64) ENCODE zstd,
        device_screen_resolution character varying(64) ENCODE zstd,
        device_language character varying(64) ENCODE zstd,
        device_country character varying(64) ENCODE zstd,
        device_memory character varying(64) ENCODE zstd,
        device_model character varying(64) ENCODE zstd,
        device_timezone character varying(64) ENCODE zstd,
        device_type character varying(64) ENCODE zstd,
        network_type character varying(64) ENCODE zstd,
        ip character varying(64) ENCODE zstd,
        local_version bigint ENCODE zstd,
        remote_version_ack bigint ENCODE zstd,
        remote_version_local bigint ENCODE zstd,
        has_login boolean ENCODE zstd,
        has_network boolean ENCODE zstd,
        current_member_type character varying(64) ENCODE zstd,
        abtests character varying(1024) ENCODE zstd,
        client_version_name character varying(64) ENCODE zstd,
        user_group_ad bigint ENCODE zstd,
        common_extras super ENCODE zstd,
        user_groups super ENCODE zstd,
        campaign_type_code bigint ENCODE zstd,
        game_scheme character varying(64) ENCODE zstd,
        sequence bigint ENCODE zstd,
        abtest_map super ENCODE zstd,
        initial_client_version character varying(32) ENCODE zstd,
        iap_count bigint ENCODE zstd,
        iap_total bigint ENCODE zstd,
        common_game_event_type character varying(128) ENCODE zstd,
        params super ENCODE zstd,
        extras super ENCODE zstd,
        time timestamp without time zone ENCODE zstd,
        load_date character varying(32) ENCODE zstd,
        user_group_ad_string character varying(65535) ENCODE lzo,
        local_version_string character varying(65535) ENCODE lzo,
        sequence_string character varying(65535) ENCODE lzo,
        campaign_type_code_string character varying(65535) ENCODE lzo,
        iap_count_string character varying(65535) ENCODE lzo,
        member_time_string character varying(65535) ENCODE lzo,
        revenue_usd_cents_string character varying(65535) ENCODE lzo,
        time_string character varying(65535) ENCODE lzo,
        iap_total_string character varying(65535) ENCODE lzo,
        installed_at_string character varying(65535) ENCODE lzo,
        member_age_string character varying(65535) ENCODE lzo,
        member_string character varying(65535) ENCODE lzo,
        has_network_string character varying(65535) ENCODE lzo,
        remote_version_local_string character varying(65535) ENCODE lzo,
        has_login_string character varying(65535) ENCODE lzo,
        remote_version_ack_string character varying(65535) ENCODE lzo,
        created_at_string character varying(65535) ENCODE lzo,
        player_id_string character varying(65535) ENCODE lzo
) DISTSTYLE KEY
SORTKEY
    (time);
"""

table_prompt_dict['guidance_haiku-20240307v1-0_20240407063835'] = """
you should always keep the words from question unchanges when writing SQL. \n\n
"""

table_prompt_dict['guidance_sonnet-20240229v1-0_20240407063835'] = """
you should always keep the words from question unchanges when writing SQL. \n\n
you should always use zenmakeovermatch as schema name. For example, use zenmakeovermatch.account instead of account\n\n
when sql question is about PV (page view) or UV (user view), you should consider event name including _page_view and _screen_view \n\n
you should always use event id to count the occurance of event name \n\n
"""
# divide the sales volume of the product or competing products rolling forward 3 months from the latest month of data by sales volume in the same time period in the market to get R3M MS% (YoY) or 滚动3个月市场占比.
# use the MS% of the product or competitive product rolled forward 3 months from the latest month of data and subtract the MS% of the same period last year to get Δ MS% (YoY) or 滚动3个月市场占比变化.

# support_funtions = ['table', 'guidance']

# support_model_ids_map = {
#     "anthropic.claude-3-haiku-20240307-v1:0":"haiku-20240307v1-0",
#     "anthropic.claude-3-sonnet-20240229-v1:0":"sonnet-20240229v1-0"
# }

# support_versions = ['20240407063835']

class SQLPromptMapper:
    def __init__(self):
        self.variable_map = table_prompt_dict

    def get_variable(self, name):
        return self.variable_map.get(name)