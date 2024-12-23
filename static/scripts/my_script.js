function copyUrls(urls, image_count=1) {
    // 将 URL 复制到剪贴板
    navigator.clipboard.writeText(urls.join('\n'));
    // 提示用户
    alert(image_count + '幅影像，共' + urls.length + '个下载链接已复制到剪贴板');
    if (image_count < 1) {
        return false;
    }
    // window.open();
    // 获取当前页面url
    let new_window =  window.open();
    let html_str = '<h1>下载链接</h1>';
    let urls_str = '';
    // 遍历URL数组， 将每个URL添加到HTML字符串中
    for(let url of urls) {
        urls_str += 'wget <a href="'+ url +'" target="_blank">'+ '"' + url + '"' +'</a><br/><br/>';
    }
    html_str += urls_str;
    
    new_window.document.body.innerHTML = html_str;
    
}

function downloadByArea() {
    // 获取输入的经纬度
    const lat_start_str = document.getElementById('input_lat_start').value;
    const lng_start_str = document.getElementById('input_lng_start').value;
    const lat_end_str = document.getElementById('input_lat_end').value;
    const lng_end_str = document.getElementById('input_lng_end').value;
    const time_start_str = document.getElementById('input_time_start').value;
    const time_end_str = document.getElementById('input_time_end').value;

    const lat_start = parseFloat(lat_start_str);
    const lng_start = parseFloat(lng_start_str);
    const lat_end = parseFloat(lat_end_str);
    const lng_end = parseFloat(lng_end_str);

    // 判断起始时间是否小于等于结束时间(为空则不判断)
    if (time_start_str !== '' && time_end_str !== '') {
        if (time_start_str > time_end_str) {
            alert('请输入正确的时间范围, 范围: 起始时间<=结束时间');
            return false;
        }
    }


    // 判断输入是否合法(不为空且为正确经纬度范围)
    if (lat_start === '' || lng_start === '' || lat_end === '' || lng_end === '') {
        alert('请输入经纬度');
        return false;
    }
    if (isNaN(lat_start) || isNaN(lng_start) || isNaN(lat_end) || isNaN(lng_end)) {
        alert('请输入正确的经纬度');
        return false;
    }
    if (lat_start < -90 || lat_start > 90 || lat_end < -90 || lat_end > 90 || lng_start < -180 || lng_start > 180 || lng_end < -180 || lng_end > 180) {
        alert('请输入正确的经纬度范围, 范围: 纬度-90~90, 经度-180~180');
        return false;
    }
    if (lat_start < lat_end || lng_start > lng_end) {
        alert('请输入正确的经纬度范围, 范围: 纬度从大到小, 经度从小到大');
        return false;
    }
    // alert('确认下载范围为: 纬度['+lat_start+'~'+lat_end+'], 经度['+lng_start+'~'+lng_end+']');
    // 发送 AJAX 请求
    $.ajax({
        url: '/download_by_area',
        type: 'GET',
        data: {
            'lat_start': lat_start,
            'lng_start': lng_start,
            'lat_end': lat_end,
            'lng_end': lng_end,
            'time_start': time_start_str,
            'time_end': time_end_str,
        },
        success: function (data) {
            // 处理返回的数据
            if (data.status === 'success') {
                copyUrls(data.urls, data.image_count);
                // alert('成功'+data.message);
            } else {
                alert('失败'+data.message);
            }
        },
    })
}
