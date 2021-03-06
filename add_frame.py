import os
import sys
import glob
import json
import requests
import exifread
from os.path import isfile, join
from os import listdir, path, remove
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps


PICTURE_FOLDER = ""
PREPROCESS_FLAG = "_2000."
MY_SPECIAL_TAG = "_lcy"
ADDITIONAL_OUTPUT_FOLDER = "_frame"
AUTHOR = ""
LOCATION_LIST_FILE_NAME = "loc.txt"
DESCRIPTION_LIST_FILE_NAME = "desc.txt"

OPTION_DEBUG = 0
OPTION_CLEAR_PICTURES = 1
OPTION_QUERY_ADDRESS = 1

RESIZE_WIDTH_LANDSCAPE = 1000
RESIZE_WIDTH_PORTRAIT = 750
RESIZE_WIDTH_SQUARE = 500
TEXT_FONT_SIZE = 14

FRAME_MODE_CLASSIC      = 1
FRAME_MODE_SHOT_PARAM   = 2
FRAME_MODE_FILM         = 4
FRAME_MODE_INSTAGRAM    = 8
FRAME_MODE_MAGNUM       = 16
FRAME_MODE_YANSELF      = 32
FRAME_MODE_G4           = 64
FRAME_MODE_NONE         = 128
FRAME_MODE_LIST         = {FRAME_MODE_CLASSIC:"CLASSIC", FRAME_MODE_SHOT_PARAM:"PARAM", FRAME_MODE_FILM:"FILM", 
                            FRAME_MODE_INSTAGRAM:"INSTA", FRAME_MODE_MAGNUM:"MAG", FRAME_MODE_YANSELF:"YANSELF", FRAME_MODE_G4:"G4", FRAME_MODE_NONE:"NONE"}
FRAME_MODE =  FRAME_MODE_NONE + FRAME_MODE_INSTAGRAM + FRAME_MODE_G4
#FRAME_MODE =  FRAME_MODE_YANSELF
is_read_mode            = 0

ORIENT_ROTATES = {"Horizontal (normal)":1, "Mirrored horizontal":2, "Rotated 180":3, "Mirrored vertical":4,
                  "Mirrored horizontal then rotated 90 CCW":5, "Rotated 90 CW":6, "Mirrored horizontal then rotated 90 CW":7, "Rotated 90 CCW":8}

def query_addr(exif):
    if "GPS GPSLongitudeRef" not in exif.keys():
        return ""
    # 经度
    lon_ref = exif["GPS GPSLongitudeRef"].printable
    lon = exif["GPS GPSLongitude"].printable[1:-1].replace(" ", "").replace("/", ",").split(",")
    if len(lon) < 4:
        return ""
    print(lon)
    if float(lon[3]) > 0.0:
        lon = float(lon[0]) + float(lon[1]) / 60 + float(lon[2]) / float(lon[3]) / 3600
    else:
        lon = float(lon[0]) + float(lon[1]) / 60
    if lon_ref != "E":
        lon = lon * (-1)
    # 纬度
    lat_ref = exif["GPS GPSLatitudeRef"].printable
    lat = exif["GPS GPSLatitude"].printable[1:-1].replace(" ", "").replace("/", ",").split(",")
    if len(lat) < 4:
        return ""
    if float(lat[3]) > 0.0:
        lat = float(lat[0]) + float(lat[1]) / 60 + float(lat[2]) / float(lat[3]) / 3600
    else:
        lat = float(lat[0]) + float(lat[1]) / 60
    if lat_ref != "N":
        lat = lat * (-1)
    #print('照片的经纬度：', (lat, lon))
    # 调用百度地图api转换经纬度为详细地址
    secret_key = '1flkRi6QA71FrifGk4yFEB6jGtWOpFxC' # 百度地图api 填入你自己的key
    baidu_map_api = 'http://api.map.baidu.com/reverse_geocoding/v3/?ak={}&output=json&coordtype=wgs84ll&location={},{}'.format(secret_key, lat, lon)
    content = requests.get(baidu_map_api).text
    gps_address = json.loads(content)
    # 结构化的地址
    formatted_address = gps_address["result"]["formatted_address"]
    # 国家（若需访问境外POI，需申请逆地理编码境外POI服务权限）
    country = gps_address["result"]["addressComponent"]["country"]
    # 省
    province = gps_address["result"]["addressComponent"]["province"]
    # 市
    city = gps_address["result"]["addressComponent"]["city"]
    # 区
    district = gps_address["result"]["addressComponent"]["district"]
    # 街
    street = gps_address["result"]["addressComponent"]["street"]
    # 语义化地址描述
    sematic_description = gps_address["result"]["sematic_description"]
    #print(formatted_address)
    #print(city)
    #print(street)
    #print(gps_address["result"]["business"])
    idx = street.find("路")
    if idx != -1:
        street = street[0:idx+1]
    return street + " " + city.replace("市", "")


def draw_frame(ctx, x, y, width, height, color, line_width):
    offset = 2
    ctx.line((x-offset, y, x+width+offset, y), color, line_width)
    ctx.line((x+width, y, x+width, y+height), color, line_width+1)
    ctx.line((x+width+offset, y+height, x-offset, y+height), color, line_width)
    ctx.line((x, y+height, x, y), color, line_width+1)

def get_frame_rect_instagram(resize_width, resize_height):
    # calculate frame size
    frame_width = resize_width
    frame_width += (frame_width % 2)
    frame_height = frame_width
    if resize_width == resize_height:
        frame_width = (int)(resize_width * 1.6)
        frame_width += (frame_width % 2)
        frame_height = frame_width
    elif resize_width < resize_height:
        frame_width = (int)(resize_width * 1.7)
        frame_width += (frame_width % 2)
        frame_height = frame_width

    # calculate picture's left/top
    left = (int)((frame_width - resize_width) / 2.0)
    top = (int)((frame_height - resize_height) / 2.0)
    if resize_width == resize_height:
        left = (int)((frame_width - resize_width) / 2.0)
        top = (int)((frame_height - resize_height) / 2.0)
    elif resize_width < resize_height:
        left = (int)(frame_width * 0.05) 
        top = (int)((frame_height - resize_height) / 2)

    # calculate postion of text
    text_left = left + 2
    text_top = top + resize_height + 2
    if resize_width < resize_height:
        text_left = left + resize_width + 8
        text_top = top + resize_height - 16
    elif resize_width == resize_height:
        text_left = left
        text_top = top + resize_height + 2
    return (left, top, frame_width, frame_height, (255, 255, 255), text_left, text_top)    

def get_frame_rect_magnum(resize_width, resize_height):
    # calculate frame size
    frame_width = (int)(resize_width * 1.02)
    frame_width += (frame_width % 2)
    frame_height = frame_width
    if resize_width == resize_height:
        frame_width = (int)(resize_width * 1.6)
        frame_width += (frame_width % 2)
        frame_height = frame_width
    elif resize_width < resize_height:
        frame_width = (int)(resize_width * 1.7)
        frame_width += (frame_width % 2)
        frame_height = frame_width

    # calculate picture's left/top
    left = (int)((frame_width - resize_width) / 2.0)
    top = (int)((frame_height - resize_height) / 2.0)
    if resize_width == resize_height:
        left = (int)((frame_width - resize_width) / 2.0)
        top = (int)((frame_height - resize_height) / 2.0)
    elif resize_width < resize_height:
        left = (int)(frame_width * 0.05) 
        top = (int)((frame_height - resize_height) / 2)

    # calculate postion of text
    text_left = left
    text_top = top + resize_height + 2
    if resize_width < resize_height:
        text_left = left + resize_width + 8
        text_top = top + resize_height - 22
    elif resize_width == resize_height:
        text_left = left
        text_top = top + resize_height + 2
    return (left, top, frame_width, frame_height, (255, 255, 255), text_left, text_top)    

def get_frame_rect_yanself(resize_width, resize_height):
    # calculate frame size
    frame_width = (int)(resize_width * 1.02)
    frame_width += (frame_width % 2)
    frame_height = frame_width
    if resize_width == resize_height:
        frame_width = (int)(resize_width * 1.6)
        frame_width += (frame_width % 2)
        frame_height = frame_width
    elif resize_width < resize_height:
        frame_width = (int)(resize_width * 1.02)
        frame_width += (frame_width % 2)
        frame_height = (int)(resize_height * 1.2)

    # calculate picture's left/top
    left = (int)((frame_width - resize_width) / 2.0)
    top = (int)((frame_height - resize_height) / 2.0)
    if resize_width == resize_height:
        left = (int)((frame_width - resize_width) / 2.0)
        top = (int)((frame_height - resize_height) / 2.0)
    elif resize_width < resize_height:
        left = (int)((frame_width - resize_width) / 2.0)
        top = (int)((frame_height - resize_height) / 2.0)
     # calculate postion of text
    text_left = left
    text_top = top + resize_height + 2
    if resize_width < resize_height:
        text_left = left
        text_top = top + resize_height + 2
    elif resize_width == resize_height:
        text_left = left
        text_top = top + resize_height + 2
    return (left, top, frame_width, frame_height, (255, 255, 255), text_left, text_top)    

def get_frame_rect_g4(resize_width, resize_height):
    # calculate frame size
    frame_width = (int)(resize_width * 1.02)
    frame_width += (frame_width % 2)
    frame_height = (int)(resize_height * 1.18)
    if resize_width == resize_height:
        frame_width = (int)(resize_width * 1.6)
        frame_width += (frame_width % 2)
        frame_height = frame_width
    elif resize_width < resize_height:
        frame_width = (int)(resize_width * 1.03)
        frame_width += (frame_width % 2)
        frame_height = (int)(resize_height * 1.2)

    # calculate picture's left/top
    left = (int)((frame_width - resize_width) / 2.0)
    top = (int)((frame_height - resize_height) / 2.0)
    if resize_width == resize_height:
        left = (int)((frame_width - resize_width) / 2.0)
        top = (int)((frame_height - resize_height) / 2.0)
    elif resize_width < resize_height:
        left = (int)((frame_width - resize_width) / 2.0)
        top = (int)((frame_height - resize_height) / 2.0)
     # calculate postion of text
    text_left = left
    text_top = top + resize_height + 2
    if resize_width < resize_height:
        text_left = left
        text_top = top + resize_height + 2
    elif resize_width == resize_height:
        text_left = left
        text_top = top + resize_height + 2
    return (left, top, frame_width, frame_height, (255, 255, 255), text_left, text_top) 

def get_frame_rect_classic(resize_width, resize_height):
    # calculate frame size
    frame_width = (int)(resize_width * 1.13)
    frame_width += (frame_width % 2)
    frame_height = (int)(frame_width * 0.89)
    frame_height += (frame_height % 2)
    if resize_width < resize_height:
        frame_width = (int)(resize_width * 1.7)
        frame_width += (frame_width % 2)
        frame_height = frame_width
    elif resize_width == resize_height:
        frame_width = (int)(resize_width * 1.2)
        frame_width += (frame_width % 2)
        frame_height = (int)(frame_width * 1.2)
        frame_height += (frame_height % 2)

    # calculate picture's left/top
    left = (int)((frame_width - resize_width) / 2.0)
    top = (int)((frame_height - resize_height) / 4.1)
    if resize_width < resize_height:
        left = (int)(frame_width * 0.05) 
        top = (int)((frame_height - resize_height) / 2)
    elif resize_width == resize_height:
        left = (int)((frame_width - resize_width) / 2.0)
        top = (int)((frame_height - resize_height) / 2.0) - (int)((frame_height - frame_width) / 2.0)

    # calculate postion of text
    text_left = left
    text_top = top + resize_height + 2
    if resize_width < resize_height:
        text_left = left + resize_width + 8
        text_top = top + resize_height - 16
    return (left, top, frame_width, frame_height, (255, 255, 255), text_left, text_top)

def get_frame_rect_none(resize_width, resize_height):
    return (0, 0, resize_width, resize_height, (255, 255, 255), 0, 0)

def get_frame_rect(frame_mode, resize_width, resize_height):
    if frame_mode == FRAME_MODE_CLASSIC:
        return get_frame_rect_classic(resize_width, resize_height)
    if frame_mode == FRAME_MODE_INSTAGRAM:
        return get_frame_rect_instagram(resize_width, resize_height)
    if frame_mode == FRAME_MODE_MAGNUM:
        return get_frame_rect_magnum(resize_width, resize_height)    
    if frame_mode == FRAME_MODE_YANSELF:
        return get_frame_rect_yanself(resize_width, resize_height)    
    if frame_mode == FRAME_MODE_G4:
        return get_frame_rect_g4(resize_width, resize_height)    
    if frame_mode == FRAME_MODE_NONE:
        return get_frame_rect_none(resize_width, resize_height)    
    return get_frame_rect_classic(resize_width, resize_height)

def get_basic_info(frame_mode, exif):
    # imgexif = open(input_file, 'rb')
    # exif = exifread.process_file(imgexif)
    # for key in exif.keys():
    #    print("tag: %s, value: %s" % (key, exif[key]))

    # shot time
    shot_time = "unkown shot time"
    date_time = ""
    if "EXIF DateTimeOriginal" in exif.keys():
        shot_time = exif["EXIF DateTimeOriginal"].printable
        date_time = shot_time.split(" ", 1)[0]
        date_time = date_time.split(":")
        date_time = ("%s.%02d.%02d" % (date_time[0][0:4], int(date_time[1]), int(date_time[2])))
        # if frame_mode == FRAME_MODE_MAGNUM or frame_mode == FRAME_MODE_YANSELF:
        #     date_time = ("%s.%d.%d" % (date_time[0][0:4], int(date_time[1]), int(date_time[2])))
        # else:
        #     date_time = ("%d %d '%s" % (int(date_time[1]), int(date_time[2]), date_time[0][2:4]))
    # for NOMO film
    desc = ""
    if "Image ImageDescription" in exif.keys():
        desc = exif["Image ImageDescription"].printable
        desc = desc.strip()
        idx = desc.find("NOMO")
        if desc != "" and  -1 != idx:
            desc = desc[(idx+len("NOMO ")):(len(desc)-1)]
    if frame_mode == FRAME_MODE_SHOT_PARAM:
        if "EXIF FNumber" in exif.keys():
            desc = desc + " F" + exif["EXIF FNumber"].printable
        if "EXIF ExposureTime" in exif.keys():
            desc = desc + " " + exif["EXIF ExposureTime"].printable
        if "EXIF ISOSpeedRatings" in exif.keys():
            desc = desc + " ISO" + exif["EXIF ISOSpeedRatings"].printable
        # if "EXIF ExposureBiasValue" in exif.keys():
        #     ev = float(exif["EXIF ExposureBiasValue"]) * 100.0 / 33.0    
        #     desc = desc + (" EV%d", ev)
        # if "EXIF ExposureMode" in exif.keys():
        #     desc = desc + " ExpM" + exif["EXIF ExposureMode"].printable
        if "EXIF FocalLengthIn35mmFilm" in exif.keys():
            desc = desc + " " + exif["EXIF FocalLengthIn35mmFilm"].printable + "MM"
        elif "EXIF FocalLength" in exif.keys():
            desc = desc + " " + exif["EXIF FocalLength"].printable + "MM"
        if "EXIF ExposureProgram" in exif.keys():
            desc = desc + " " + exif["EXIF ExposureProgram"].printable            
        if "EXIF ColorSpace" in exif.keys():
            desc = desc + " " + exif["EXIF ColorSpace"].printable
    return (date_time, shot_time, desc)

def check_orientation(image, exif):
    orientation = 1
    if "Image Orientation" in exif.keys():
        orientation = ORIENT_ROTATES[exif["Image Orientation"].printable]
    if orientation == 1:
        return image
    elif orientation == 2:
        # left-to-right mirror
        return ImageOps.mirror(image)
    elif orientation == 3:
        # rotate 180
        return image.transpose(Image.ROTATE_180)
    elif orientation == 4:
        # top-to-bottom mirror
        return ImageOps.flip(image)
    elif orientation == 5:
        # top-to-left mirror
        return ImageOps.mirror(image.transpose(Image.ROTATE_270))
    elif orientation == 6:
        # rotate 270
        return image.transpose(Image.ROTATE_270)
    elif orientation == 7:
        # top-to-right mirror
        return ImageOps.mirror(image.transpose(Image.ROTATE_90))
    elif orientation == 8:
        # rotate 90
        return image.transpose(Image.ROTATE_90)    
    else:
        return image    

def get_resize_size(frame_mode, origin_width, origin_height, origin_file):
    resize_width = RESIZE_WIDTH_LANDSCAPE
    if origin_width < origin_height:
        resize_width = RESIZE_WIDTH_PORTRAIT
    elif origin_width == origin_height:
        resize_width = RESIZE_WIDTH_SQUARE
    wpercent = (resize_width/float(origin_file.size[0]))
    resize_height = int((float(origin_file.size[1])*float(wpercent)))
    if frame_mode == FRAME_MODE_MAGNUM or frame_mode == FRAME_MODE_YANSELF or frame_mode == FRAME_MODE_INSTAGRAM:
        resize_width = (int)(resize_width * 7 / 5)
        resize_height = (int)(resize_height * 7 / 5)
    elif frame_mode == FRAME_MODE_NONE:
        resize_width *= 2
        resize_height *= 2 
    resize_width += (resize_width % 2)
    return resize_width, resize_height

def read_location_file():
    loc_file_path = PICTURE_FOLDER + "/" + LOCATION_LIST_FILE_NAME
    is_exist = os.path.exists(loc_file_path)
    if is_exist == False:
        return None
    locs = list()
    loc_list = open(loc_file_path, 'r')
    for line in loc_list.readlines():
        locs.append(line.strip())
    print(locs)
    return locs

def read_description_file():
    desc_file_path = PICTURE_FOLDER + "/" + DESCRIPTION_LIST_FILE_NAME
    is_exist = os.path.exists(desc_file_path)
    if is_exist == False:
        return None
    descs = list()
    desc_list = open(desc_file_path, 'r')
    for line in desc_list.readlines():
        descs.append(line.strip())
    print(descs)
    return descs

def add_frame(input_file, output_path, loc=None, desc=None):
    imgexif = open(input_file, 'rb')
    exif = exifread.process_file(imgexif)

    # GPS
    location = ""
    if loc != None and len(loc) > 0:
        location = loc
    else:
        if OPTION_QUERY_ADDRESS == 1:
            location = query_addr(exif)
            if len(location) <= 0:
                location = "上海"
                print("unknown location, set deafult: %s" % location)
    print(location)

    # check landscape or portrait
    origin_file = Image.open(input_file).convert("RGBA")
    origin_file = check_orientation(origin_file, exif)
    origin_width, origin_height = origin_file.size
    is_landscape = (origin_width > origin_height)
    
    for mode in FRAME_MODE_LIST:
        if mode & FRAME_MODE != mode:
            continue
        resize_width, resize_height = get_resize_size(mode, origin_width, origin_height, origin_file)
        # font size
        font_size = TEXT_FONT_SIZE
        if is_landscape == True:
            if resize_width > 1200:
                font_size = 30
        else:
            if resize_height > 800:
                font_size = 30  
        # resize picture
        img_resize = origin_file.resize((resize_width, resize_height), Image.ANTIALIAS)

        loc = location
        # remove location info for instagram
        if mode == FRAME_MODE_INSTAGRAM:
            loc = ""
        date_time, shot_time, exif_desc = get_basic_info(mode, exif)
        left, top, frame_width, frame_height, bg_color, text_left, text_top = get_frame_rect(mode, resize_width, resize_height)

        # create background image
        img_frame = Image.new('RGBA', (frame_width, frame_height), bg_color)

        # overlay picture
        img_frame.paste(img_resize, (left, top))

        # draw text
        text_top += 2
        text_top_offset = 22
        text_color = (200, 200, 200)
        if mode == FRAME_MODE_MAGNUM or mode == FRAME_MODE_YANSELF:
            text_color = (88, 88, 88)
            text_top_offset = 32
            
        font = ImageFont.truetype("FZWBJW.TTF", font_size)
        draw = ImageDraw.Draw(img_frame)
        if resize_width >= resize_height:
            if mode == FRAME_MODE_INSTAGRAM or mode == FRAME_MODE_NONE:
                draw_text = ""
            else:
                draw_text = ("%s %s %s  %s" % (date_time, exif_desc, loc, desc))
                draw.text((text_left, text_top), draw_text, font=font, fill=text_color)
                if mode == FRAME_MODE_MAGNUM:
                    draw.text((left+resize_width-50, text_top), AUTHOR, font=font, fill=text_color)
        else:
            if mode == FRAME_MODE_YANSELF or mode == FRAME_MODE_G4:
                draw_text = ("%s %s %s  %s" % (date_time, exif_desc, loc, desc))
                draw.text((text_left, text_top), draw_text, font=font, fill=text_color)
            elif mode == FRAME_MODE_INSTAGRAM or mode == FRAME_MODE_NONE:
                draw_text = ""
            else:
                draw_text = ("%s  %s" % (date_time, exif_desc))
                draw.text((text_left, text_top), draw_text, font=font, fill=text_color)
                if loc != "":                   
                    draw.text((text_left, text_top - text_top_offset), loc, font=font, fill=text_color)
                if mode == FRAME_MODE_MAGNUM:
                    draw.text((text_left, text_top - text_top_offset * 2), AUTHOR, font=font, fill=text_color)
        

        # draw frame line
        # draw_frame(draw, 0, 0, frame_width, frame_height, "black", 12)
        # draw_frame(draw, left, top, resize_width, resize_height, "black", 3)

        # calculate output file path
        riginal_path, original_file_name = path.split(input_file)
        output_name, output_ext_name = path.splitext(original_file_name)
        output_name = FRAME_MODE_LIST[mode] + "_" + output_name
        text_time = shot_time.replace(":", "-")
        text_time = text_time.replace(" ", "_")
        output_name += ("_%s_%dx%d%s" % (text_time, frame_width, frame_height, MY_SPECIAL_TAG))
        output_name += output_ext_name
        #output_folder = ("%s/%s" % (riginal_path, ADDITIONAL_OUTPUT_FOLDER))
        output_folder = output_path
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
        output_full_path = ("%s/%s" % (output_folder, output_name))

        # show picture used for debug
        if OPTION_DEBUG == 1:
            img_frame.show()

        # write file
        img_frame = img_frame.convert("RGB")
        img_frame.save(output_full_path, quality=100)
        #shutil.copy(output_name, additional_output_path)
        print(output_full_path)
        # end of for loop
    return (date_time, location, desc)

def search_files(dirname):
    filter = [".jpg", ".JPG", ".jpeg", ".JPEG"]
    result = []

    for filename in os.listdir(dirname):
        apath = os.path.join(dirname, filename)
        ext = os.path.splitext(apath)[1]
        if ext in filter:
            if -1 == apath.find(MY_SPECIAL_TAG):
                if PREPROCESS_FLAG == "" or -1 != apath.find(PREPROCESS_FLAG):
                    result.append(apath)
    result = sorted(result)

    # serach sub-folder
    # for maindir, subdir, file_name_list in os.walk(dirname):
    #     for filename in file_name_list:
    #         apath = os.path.join(maindir, filename)#合并成一个完整路径
    #         ext = os.path.splitext(apath)[1]  # 获取文件后缀 [0]获取的是除了文件名以外的内容
    #         if ext in filter:
    #             if -1 == apath.find(MY_SPECIAL_TAG):
    #                 if PREPROCESS_FLAG == "" or -1 != apath.find(PREPROCESS_FLAG):
    #                     result.append(apath)
    return result

def dump_picture_infos(infos, full_additional_path):
    if len(infos) == 0:
        return
    file_name = full_additional_path + "/_infos.txt"
    file_handle = open(file_name, "w")
    for info in infos:
        txt = ("%d) %s %s  %s\n" % (info[0], info[1], info[2], info[3]))
        file_handle.write(txt)
    file_handle.close()
    print("dump successfully!", file_name)

def resize_photo(file_path, max_width):
    imgexif = open(file_path, 'rb')
    exif = exifread.process_file(imgexif)
    origin_file = Image.open(file_path).convert("RGBA")
    origin_file = check_orientation(origin_file, exif)
    origin_width, origin_height = origin_file.size
    is_landscape = (origin_width > origin_height)

    resize_width = 0
    resize_height = 0
    if is_landscape is True:
        resize_width = max_width
        resize_height = int(resize_width * origin_height / origin_width)
    else:
        resize_height = max_width
        resize_width = int(resize_height * origin_width / origin_height)

    img = origin_file.resize((resize_width, resize_height), Image.ANTIALIAS)
    return img, exif


def search_files2(dirname):
    filter = [".jpg", ".JPG", ".jpeg", ".JPEG"]
    result = []
    for filename in os.listdir(dirname):
        apath = os.path.join(dirname, filename)
        ext = os.path.splitext(apath)[1]
        if ext in filter:
            result.append(apath)
    result = sorted(result)
    return result

def prepare_print(path):
    resize_width = 2000
    file_list = search_files2(path)
    for curr_path in file_list:
        handle, exif = resize_photo(curr_path, resize_width)

        desc = ""
        (path, filename) = os.path.split(curr_path)
        if "EXIF FNumber" in exif.keys():
            desc = desc + " F" + exif["EXIF FNumber"].printable
        if "EXIF ExposureTime" in exif.keys():
            desc = desc + " " + exif["EXIF ExposureTime"].printable
        if "EXIF ISOSpeedRatings" in exif.keys():
            desc = desc + " ISO" + exif["EXIF ISOSpeedRatings"].printable
        draw_text = ("%s %s" % (filename, desc))

        font = ImageFont.truetype("FZWBJW.TTF", 30)
        draw = ImageDraw.Draw(handle)
        draw.text((0, 0), draw_text, font=font, fill=(180, 180 , 180))

        output_folder = path + "/_print"
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
        output_name, output_ext_name = os.path.splitext(filename)
        output_full_path = ("%s/%s_%d%s" % (output_folder, output_name, resize_width, output_ext_name))
        # write file
        handle = handle.convert("RGB")
        handle.save(output_full_path, quality=100)
        print(output_full_path)

def usage():
	print ("""
usage: add_frame [path_of_picture][-h][-v]

arguments:
    path_of_picture	    path of JPG file
    -i                  ignore PREPROCESS_FLAG("_2000.") flag from source picture
    -c                  clear/delete all pictures on output folder before resize
    -a                  disable parse shot address from GPS info
    -m                  specify frame mode
    -d                  enable debug mode
    -h, --help			show this help message and exit
    -v, --version		show version information and exit
""")

def process():
    # search 
    files = search_files(PICTURE_FOLDER)
    if len(files) == 0:
        print("no file found. %s" % PICTURE_FOLDER)
        sys.exit()
    #print(files)
    #sys.exit()

    # create additional output folder
    full_additional_path = ("%s/%s" % (PICTURE_FOLDER, ADDITIONAL_OUTPUT_FOLDER))
    is_exist = os.path.exists(full_additional_path)
    if not is_exist:
        os.makedirs(full_additional_path)
    elif OPTION_CLEAR_PICTURES == 1:
        fileNames = glob.glob(full_additional_path + r'/*')
        for fileName in fileNames:
            os.remove(fileName)
    
    infos = list()
    location_list = read_location_file()
    description_list = read_description_file()

    # Resize the Original files.
    idx = 0
    for each_picture in files:
        print("\nNo.%04d" % (idx+1))

        loc = ""
        if location_list != None and idx < len(location_list):
            loc = location_list[idx]

        desc = ""
        if description_list != None and idx < len(description_list):
            desc = description_list[idx]
        
        shot_time, loc, desc = add_frame(each_picture, full_additional_path, loc, desc)
        infos.append((idx+1, shot_time, loc, desc))
        idx += 1
    dump_picture_infos(infos, full_additional_path)

    # print ("output folder: %s" % full_additional_path)
    print ("\nDONE.")


if __name__ == '__main__':
    if len(sys.argv) == 1:
        print("arguments error!\r\n-h shows usage.")
        PICTURE_FOLDER = "/Users/junlin/myPhoto/yanself/2021Q1/01"
        PREPROCESS_FLAG = ""
        #OPTION_DEBUG = 1
        process()
        sys.exit()
    for arg in sys.argv[1:]:
        if arg == '-v' or arg == "--version":
            print("1.0.0")
            sys.exit()
        elif arg == '-h' or arg == '--help':
            usage()
            sys.exit()
        elif arg == '-i' or arg == '--ignore':
            PREPROCESS_FLAG = ""
        elif arg == '-c' or arg == '--clear':
            OPTION_CLEAR_PICTURES = 0
        elif arg == '-a' or arg == '--address':
            OPTION_QUERY_ADDRESS = 0
        elif arg == '-m' or arg == '--mode':
            is_read_mode = 1
        elif arg == '-d' or arg == '--debug':
            OPTION_DEBUG = 1
        elif is_read_mode == 1:
            is_read_mode = 0
            FRAME_MODE = arg

    PICTURE_FOLDER = sys.argv[1]
    process()



