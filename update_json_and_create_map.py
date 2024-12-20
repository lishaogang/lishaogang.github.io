
import os
from tqdm import tqdm
import json
from folium import plugins, JsCode
import folium
import numpy as np
import boto3
from botocore import UNSIGNED
from botocore.config import Config
import logging
import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_json_paths(bucket_name):
    """
    获取指定 S3 存储桶中所有以 'stac' 开头的 JSON 文件的路径
    :param bucket_name: S3 存储桶名称
    :return: JSON 文件路径列表
    """
        
    # 创建 S3 客户端
    s3 = boto3.client('s3', config=Config(signature_version=UNSIGNED))

    # url_root = f'https://s3.us-west-2.amazonaws.com/{bucket_name}'

    # 连接到 S3 存储桶
    logger.info(f'正在连接到 S3 存储桶: {bucket_name} 以列出对象')
    paginator = s3.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=bucket_name)

    acc = 0
    json_paths = []
    # 遍历所有页面
    logger.info('正在检索文件列表')
    for page in pages:
        for obj in page['Contents']:
            if obj['Key'].startswith('stac'):
                acc += 1
                
                # json_path = os.path.join(url_root, obj['Key'])
                json_path = obj['Key']
                
                # yield json_path
                logger.info(f'检索到文件: {json_path}')
                json_paths.append(json_path)

    logger.info(f'共查询到 {acc} 个文件')
    return json_paths

def download_jsons(bucket_name='umbra-open-data-catalog', out_dir='./jsons'):
    """
    下载指定 S3 存储桶中的所有 JSON 文件，并保存到本地目录中
    :param bucket_name: S3 存储桶名称
    :param out_dir: 本地目录路径
    :return: 无
    """

    # 创建 S3 客户端
    s3 = boto3.client('s3', config=Config(signature_version=UNSIGNED))
    # 创建本地目录
    os.makedirs(out_dir, exist_ok=True)
    
    json_urls = get_json_paths(bucket_name)

    json_urls = [json_url for json_url in json_urls if not json_url.endswith('catalog.json')]
    json_names = []
    total_count = 0
    update_count = 0
    repeate_count = 0

    logger.info(f'正在下载 json 文件，总文件数:{len(json_urls)}')
    for json_path in tqdm(json_urls):
        total_count += 1

        # 下载json文件
        save_path = os.path.join(out_dir, os.path.basename(json_path))
        if os.path.exists(save_path):
            continue
        
        s3.download_file(bucket_name, json_path, save_path)
        update_count += 1

        json_name = os.path.basename(json_path)
        if json_name in json_names:
            repeate_count += 1
        else:
            json_names.append(json_name)
    

    logger.info(f'Downloaded {update_count} json files')
    logger.info(f'Found {repeate_count} repeated json files')
    logger.info(f'Total {total_count} json files')

def plot_geo_in_map(json_path, marker_cluster, json_feature_group):
    """"
    :param json_path: json 文件路径
    :param marker_cluster: marker cluster 对象
    :param json_feature_group: json feature group 对象
    :return: None
    """
    with open(json_path, 'r') as f:
        geo_data = json.load(f)
    
    geometry_type = geo_data['geometry']['type']
    assert geometry_type == 'Polygon', f'geo json 不包含影像坐标，请检查 {json_path}'

    # 提取 geojson 数据中的坐标
    # 坐标格式[[经度, 纬度, 高度]， [经度, 纬度, 高度]...]
    coordinates_data = geo_data['geometry']['coordinates']
    coordinates_data = np.array(coordinates_data).squeeze()
    coordinates_data = coordinates_data[:,:2]
    coordinates_data = coordinates_data[:,::-1]
    
    #计算中心点
    center = np.mean(coordinates_data, axis=0)
        
    sar_time_str = geo_data['properties']['datetime']

    assets_dict = geo_data['assets']
    assets_urls = [asset['href'] for asset in assets_dict.values()]

    
    #将assets_dict显示在popup上
    popup_html = ''
    popup_html += f'<p>影像ID:&emsp;{geo_data['id']}</p>'
    popup_html += f'<p>拍摄时间:&emsp;{sar_time_str}</p>'
    popup_html += f'<p>分辨率 range:&emsp;{geo_data['properties']['sar:resolution_range']}</p>'
    popup_html += f'<p>分辨率 azimuth:&emsp;{geo_data['properties']['sar:resolution_azimuth']}</p>'

    # sart_time为字符串，格式：2023-02-08T03:13:41.379001Z
    # 将其转为datetime类型仅保留T之前的部分
    sar_time_str = sar_time_str.split('T')[0]
    sart_datetime = datetime.datetime.strptime(sar_time_str, '%Y-%m-%d')
    

    for asset_name, asset in assets_dict.items():
        ext_type = asset['href'].split('.')[-1]
        popup_html += f'<p>{asset_name}:&emsp; <a href="{asset["href"]}" target="_blank">点击下载 {ext_type} 文件</a></p>'
        
    popup_html += f'<button onclick="copyUrls({assets_urls})">复制下载链接</button>'

    maker_popup = folium.Popup(folium.Html(popup_html, 
                                            script=True),
                                max_width=500,
                                )
    geo_json_popup = folium.Popup(folium.Html(popup_html, 
                                            script=True),
                                max_width=500,
                                )
    
    maker = folium.Marker(location=center, popup=maker_popup)
    maker.add_to(marker_cluster)
    # maker.add_to(folium_map)

    #将该坐标显示在世界地图上
    # geo_json_layer = folium.GeoJson(geo_data,
    #                style_function=lambda x: {'color': 'red', 'fillColor': 'red', 'weight': 5},
    #                highlight_function=lambda x: {'color': 'blue', 'fillColor': 'blue', 'weight': 5},
    #                popup=geo_json_popup,
    #                tooltip=sar_time,
    #                )
    # geo_json_layer.add_to(json_feature_group)
    folium.Polygon(coordinates_data, 
                   color='red', 
                   popup=geo_json_popup,
                   fill=True).add_to(json_feature_group)
    
    return (center, sart_datetime, assets_urls)

    

def parse_json_to_map(json_folder, out_html_path, max_item=0, static_path=''):
    """
    :param json_folder: json 文件夹路径
    :param out_html_path: 输出html文件路径
    :param max_item: 最大显示数量，为0表示显示所有
    :param static_path: Flask静态文件路径，默认为空
    :return: None
    """
    json_folder = './jsons'
    json_paths = os.listdir(json_folder)
    json_paths = [path for path in json_paths if path.endswith('.json')]

    acc = 0

    # 初始化地图
    map_size = 0.9
    input_form_size = 1-map_size

    map_size, input_form_size = str(100*map_size)+'%', str(100*input_form_size)+'%'

    folium_map = folium.Map(
                            height=map_size,
                            max_bounds=True,
                            location=[0, 0], 
                            zoom_start=3, 
                            prefer_canvas=True,
                            )
    # 鼠标位置插件
    lat_formatter = "function(num) {return 'Latitude' + L.Util.formatNum(num, 3) + ' º ';};"
    lng_formatter = "function(num) {return 'Longitude' + L.Util.formatNum(num, 3) + ' º ';};"
    plugins.MousePosition(
        position="topright",
        separator=" | ",
        empty_string="NaN",
        lng_first=True,
        num_digits=20,
        prefix="Coor: ",
        lat_formatter=lat_formatter,
        lng_formatter=lng_formatter).add_to(folium_map)
    
    # 鼠标点击位置插件
    # folium_map.add_child(folium.LatLngPopup())

    # 全屏插件
    plugins.Fullscreen(position='topleft', title='Full Screen', 
                       title_cancel='Exit Full Screen', 
                       force_separate_button=True).add_to(folium_map)

    # 添加图层控制插件，json为多边形，marker为标记点，点击可显示/隐藏
    json_feature_group = folium.FeatureGroup(name='多边形')
    marker_feature_group = folium.FeatureGroup(name='标记点')
    gaode_feature_group = folium.FeatureGroup(name='高德地图', show=False)

    # 添加高德地图图层
    tiles = 'https://webst02.is.autonavi.com/appmaptile?style=6&x={x}&y={y}&z={z}'
    gaode_map = folium.TileLayer(
        tiles=tiles,
        attr='高德地图',
        name='高德地图',
        max_zoom=18,
        min_zoom=3)
    gaode_map.add_to(gaode_feature_group)
    
    
    # 添加MarkerCluster，当标记点过多时自动聚合，避免浏览器卡顿
    marker_cluster = plugins.MarkerCluster()
    marker_cluster.add_to(marker_feature_group)
    
    # 添加OverlappingMarkerSpiderfier，当标记点重叠时自动展开，避免标记点被覆盖
    oms = plugins.OverlappingMarkerSpiderfier()
    oms.add_to(folium_map)

    # 添加绘图控件
    js_code =  '''
        function(event) {
        geo_json = this.toGeoJSON()

        let coordinates = geo_json.geometry.coordinates[0]
        let start_point = coordinates[1]
        let end_point = coordinates[coordinates.length-2]
        
        let lng_start = start_point[0]
        let lat_start = start_point[1]
        let lng_end = end_point[0]
        let lat_end = end_point[1]

        // 获取输入框， id为input_lat_start
        let input_lat_start = document.getElementById('input_lat_start')
        let input_lng_start = document.getElementById('input_lng_start')
        let input_lat_end = document.getElementById('input_lat_end')
        let input_lng_end = document.getElementById('input_lng_end')

        input_lat_start.value = lat_start
        input_lng_start.value = lng_start
        input_lat_end.value = lat_end
        input_lng_end.value = lng_end
    }
    '''
    draw_plugin = plugins.Draw(
        show_geometry_on_click=False,
        draw_options={
            'polyline': False,
            'circle': False,
            'rectangle': True,
            'polygon': False,
            'marker': False,
            'circlemarker': False
        },
        on={
            "click": JsCode(js_code)
    },
    )
    draw_plugin.add_to(folium_map)

    # 将geo json显示到map上
    logger.info(f'将所有影像区域显示在地图上, 总数:{len(json_paths)}')
    
    # 坐标及对应的影像资源链接
    urls_infos = []

    for json_path in tqdm(json_paths):
        json_path = os.path.join(json_folder, json_path)
        url_info = plot_geo_in_map(json_path, marker_cluster, json_feature_group)
        urls_infos.append(url_info)
        
        # 限制最多显示多少个geo json
        acc += 1
        if acc >= max_item and max_item > 0:
            break
    
    # 将图层添加到地图上
    gaode_feature_group.add_to(folium_map)
    json_feature_group.add_to(folium_map)
    marker_feature_group.add_to(folium_map)
    folium.LayerControl().add_to(folium_map)


    #将./static/scripts下的所有js文件添加到html文件中
    script_path = os.path.join(static_path, 'scripts')
    for js_file in os.listdir(script_path):
        if js_file.endswith('.js'):
            folium_map.get_root().html.add_child(folium.JavascriptLink(os.path.join(script_path, js_file)))

    #将./static/css下的所有css文件添加到html文件中
    css_path = os.path.join(static_path, 'css')
    for css_file in os.listdir(css_path):
        if css_file.endswith('.css'):
            folium_map.get_root().header.add_child(folium.CssLink(os.path.join(css_path, css_file)))

    # 添加根据坐标范围获取下载链接的控件
    # download_by_area_html_path = './static/html/download_by_area.html'
    # with open(download_by_area_html_path, 'r', encoding='utf-8') as f:
    #     batch_download_html = f.read()

    input_form_html = '''
        <form>
            <div class="form-group">
                <label>起始经度(Longitude):</label>
                <input type="number" class="form-control" id="input_lng_start" name="input_lng_start" placeholder="起始经度">
                <label>起始时间(空则不限制起始时间):</label>
                <input type="date" class="form-control" id="input_time_start" name="input_time_start" placeholder="起始时间">
            </div>
            <div class="form-group">
                <label>起始纬度(Latitude):</label>
                <input type="number" class="form-control" id="input_lat_start" name="input_lat_start" placeholder="起始纬度">
            </div>
            
            <div class="form-group">
                <label>结束经度(Longitude):</label>
                <input type="number" class="form-control" id="input_lng_end" name="input_lng_end" placeholder="结束经度">
                <label>结束时间(空则不限制结束时间):</label>
                <input type="date" class="form-control" id="input_time_end" name="input_time_end" placeholder="结束时间">
            </div>
            <div class="form-group">
                <label>结束纬度(Latitude):</label>
                <input type="number" class="form-control" id="input_lat_end" name="input_lat_end" placeholder="结束纬度">
            </div>
            <div class="form-group">
                <button type="button" class="btn btn-primary" onclick="downloadByArea()">获取下载链接</button>
            </div>
        </form>
    '''

    folium_map.get_root().html.add_child(folium.Html(input_form_html, 
                                                     height=input_form_size,
                                                     script=True))
    
    # 保存地图为html文件
    if out_html_path:
        logger.info(f'正在保存 {out_html_path} ...')
        folium_map.save(out_html_path)  
        logger.info(f'保存成功')
    
    return folium_map, urls_infos

def create_map(out_html_path = None, update_json = False, max_item = 0, static_path = ''):
    """
    :param out_html_path: 保存的html文件路径
    :param static_path: Flask静态文件路径
    :return:
    """
    bucket_name='umbra-open-data-catalog'
    geo_json_dir=r'./jsons'
    
    if update_json:
        download_jsons(bucket_name, geo_json_dir)
    else:
        logger.info('跳过下载json文件...')
    
    folium_map, urls_infos = parse_json_to_map(geo_json_dir, out_html_path, max_item, static_path)
    return urls_infos

