from flask import Flask, request, make_response, jsonify, render_template
from update_json_and_create_map import create_map
import logging
import os
import datetime


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

out_html_path = 'index.html'
template_path = './'
static_path = './static'

logger.info('Flask app started')

app = Flask(__name__, template_folder=template_path, static_folder=static_path)

# 获取所有影像坐标及其对应资源url
update_json = True
urls_infos = create_map(os.path.join(template_path, out_html_path), 
                        update_json=update_json, 
                        static_path=static_path)


@app.route('/')
def index():
    logger.info('Request received')
    return render_template(out_html_path)

def query_urls_by_coordinates(lat_start, lng_start, lat_end, lng_end, time_start_str, time_end_str):
    # coordinates_data [
    # [[lat, lng], urls], [[lat, lng], urls], ...
    # ]
    # 根据坐标范围筛选出符合要求的urls
    global urls_infos
    urls = []
    image_count = 0
    time_start = None
    time_end = None
    if time_start_str != '':
        time_start = datetime.datetime.strptime(time_start_str, '%Y-%m-%d')
    if time_end_str != '':
        time_end = datetime.datetime.strptime(time_end_str, '%Y-%m-%d')

    for coordinate, sar_datatime, urls_list in urls_infos:
        lat, lng = coordinate
        # 判断时间是否在范围内， sar_datatime、time_start、time_end均为datetime对象
        if time_start and sar_datatime < time_start:
            continue
        if time_end and sar_datatime > time_end:
            continue

        #判断坐标是否在范围内
        if lat_start < lat or lat < lat_end:
            continue
        if lng_start > lng or lng > lng_end:
            continue

        urls.extend(urls_list)
        image_count += 1
    return urls, image_count

    

@app.route('/download_by_area', methods=['GET'])
def download_by_area():
    logger.info('Request  download_by_area received')
    lat_start = request.args.get('lat_start')
    lng_start = request.args.get('lng_start')
    lat_end = request.args.get('lat_end')
    lng_end = request.args.get('lng_end')
    time_start_str = request.args.get('time_start')
    time_end_str = request.args.get('time_end')


    logger.info(f'lat_start: {lat_start}, lng_start: {lng_start}, lat_end: {lat_end}, lng_end: {lng_end}')
    logger.info('Querying URLs by coordinates...')

    
    urls, image_count = query_urls_by_coordinates(float(lat_start), float(lng_start),
                                                   float(lat_end), float(lng_end),
                                                   time_start_str, time_end_str
                                                   )
    logger.info(f'Found {len(urls)} URLs')

    response = make_response(jsonify({
        'status': 'success',
        'message': 'Data downloaded successfully',
        'urls': urls,
        'image_count' : image_count
        }))
    response.status_code = 200
    return response

@app.route('/draw', methods=['POST'])
def draw_event():
    data = request.form['data']
    logger.info(f'Received data: {data}')
    return


if __name__ == '__main__':
    app.run(debug=False)