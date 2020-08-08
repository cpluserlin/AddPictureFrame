import sys
import os
from os import listdir, path, remove
from os.path import isfile, join
import exifread
from PIL import Image, ImageDraw, ImageFont, ImageFilter
#import jpeg

main_folder = path.realpath(path.dirname(__file__))
#picture_folder = path.join(main_folder, "original")
picture_folder = ""
preprocess_flag = "_2000."
my_special_tag = "_lcy"

resize_width_landscape = 1000
resize_width_portrait = 530

def draw_frame(ctx, x, y, width, height, color, line_width):
    offset = 2
    ctx.line((x-offset, y, x+width+offset, y), color, line_width)
    ctx.line((x+width, y, x+width, y+height), color, line_width+1)
    ctx.line((x+width+offset, y+height, x-offset, y+height), color, line_width)
    ctx.line((x, y+height, x, y), color, line_width+1)

def add_frame(input_file):
    # check landscape or portrait
    img_resize = Image.open(input_file).convert("RGBA")
    origin_width, origin_height = img_resize.size
    is_landscape = (origin_width >= origin_height)

    # calculate resize's height
    resize_width = resize_width_landscape
    wpercent = (resize_width/float(img_resize.size[0]))
    resize_height = int((float(img_resize.size[1])*float(wpercent)))

    # calculate frame size
    frame_width = (int)(resize_width * (800.0/710.0))
    frame_width += (frame_width % 2)
    frame_height = (int)(frame_width * 710.0/800.0)
    frame_height += (frame_height % 2)

    # calculate picture's left/top
    left = (int)((frame_width - resize_width) / 2)
    top = (int)((frame_height - resize_height) / 3)

    # resize picture
    img_resize = img_resize.resize((resize_width, resize_height), Image.ANTIALIAS)

    # create background image
    img_frame = Image.new('RGBA', (frame_width, frame_height), (255, 255, 255))

    # overlay picture
    img_frame.paste(img_resize, (left, top))

    # draw text
    font = ImageFont.truetype('Arial.ttf', 18)
    draw = ImageDraw.Draw(img_frame)
    imgexif = open(input_file, 'rb')
    exif = exifread.process_file(imgexif)
    # for tag in exif.keys():
    #     print("tag: %s, value: %s" % (tag, exif[tag]))
    shot_time = exif["EXIF DateTimeOriginal"].printable
    text = shot_time
    if text == "":
        text = "unkown shot time"
    draw.text((left, top + resize_height + 10), text, font=font, fill=(230, 230, 230))

    # draw frame line
    draw_frame(draw, 0, 0, frame_width, frame_height, "black", 10)
    draw_frame(draw, left, top, resize_width, resize_height, "black", 3)

    # claculate output file path
    output_name, output_ext_name = path.splitext(input_file)
    tag = shot_time.replace(":", "-")
    tag = tag.replace(" ", "_")
    output_name += ("_%dx%d_%s%s" % (frame_width, frame_height, tag, my_special_tag))
    output_name += output_ext_name

    # write file
    # img_frame.show()
    img_frame = img_frame.convert("RGB")
    img_frame.save(output_name)
    print(output_name)

def GetMeThePictures(mypath):
    OriginalPictures = [f for f in listdir(mypath) if isfile(join(mypath, f))]
    return OriginalPictures

def search_files(dirname):
    filter = [".jpg", ".JPG", ".jpeg", ".JPEG"]
    result = []

    for maindir, subdir, file_name_list in os.walk(dirname):
        # print("1:",maindir) #当前主目录
        # print("2:",subdir) #当前主目录下的所有目录
        # print("3:",file_name_list)  #当前主目录下的所有文件
        for filename in file_name_list:
            apath = os.path.join(maindir, filename)#合并成一个完整路径
            ext = os.path.splitext(apath)[1]  # 获取文件后缀 [0]获取的是除了文件名以外的内容
            if ext in filter:
                if -1 == apath.find(my_special_tag):
                    if preprocess_flag == "" or -1 != apath.find(preprocess_flag):
                        result.append(apath)
    return result

def usage():
	print ("""
usage: add_frame [path_of_picture][-h][-v]

arguments:
    path_of_picture	    path of JPG file
    -i                  ignore preprocess_flag("_2000.") flag from source picture
    -h, --help			show this help message and exit
    -v, --version		show version information and exit
""")


if __name__ == '__main__':
    if len(sys.argv) == 1:
        print("arguments error!\r\n-h shows usage.")
        #picture_folder = "/Users/junlin/myPhoto/from_mobile/film"
        sys.exit()
    for arg in sys.argv[1:]:
        if arg == '-v' or arg == "--version":
            print("1.0.0")
            sys.exit()
        elif arg == '-h' or arg == '--help':
            usage()
            sys.exit()
        elif arg == '-i' or arg == '--ignore':
            preprocess_flag = ""
    picture_folder = sys.argv[1]


    # search 
    files = search_files(picture_folder)
    if len(files) == 0:
        print("no file found. %s" % picture_folder)
        sys.exit()
    print(files)

    # Resize the Original files.
    for each_picture in files:
        add_frame(each_picture)

    print ("Done.")