from imageai.Detection import ObjectDetection
import copy
import cv2
import csv
import time
import datetime
import os
import dotenv
import telebot
from PIL import Image


# Наша функция, в которой будет происходить вся магия
def garage_detection():
    # Теперь можно импортировать токены
    dotenv.load_dotenv('.env')
    TOKEN = os.environ['TOKEN']
    CHAT_ID = os.environ['CHAT_ID']
    CAMERA = os.environ['CAMERA']
    PROBABILITY = int(os.environ['PROBABILITY'])
    FREQUENCY = int(os.environ['FREQUENCY'])

    if CAMERA.isdigit():
        CAMERA = int(CAMERA)

    # Создадим пару констант, которые нам пригодятся
    finish = 0
    time_between_frames = FREQUENCY
    minimum_percentage_probability = PROBABILITY
    names_with_coords = {}
    old_objects_count = {'person': 0, 'car': 0, 'truck': 0}

    # Создадим объект камеры
    camera = cv2.VideoCapture(CAMERA)

    # Создадим модель
    detector = ObjectDetection()
    detector.setModelTypeAsYOLOv3()
    detector.setModelPath('yolo.h5')
    detector.loadModel()

    # Выберем только нужные объекты
    custom_objects = detector.CustomObjects(person=True, car=True, truck=True)

    # Запустим бота
    bot = telebot.TeleBot(TOKEN)

    # Запускаем камеру
    while camera.isOpened():
        # считываем данные с камеры
        ret, frame = camera.read()

        # Начало итерации
        start = time.time()

        # Таким способом можем задавать время между кадрами
        if start - finish > time_between_frames:

            # Распознаем объекты на кадре и уберем все лишнее
            _, array_detection = detector.detectObjectsFromImage(
                input_image=frame, input_type='array', output_type='array',
                minimum_percentage_probability=minimum_percentage_probability,
                custom_objects=custom_objects
            )

            # Время конца итерации
            finish = time.time()

            # Выведем список с обнаруженными объектами в консоль
            print(array_detection)

            # Создадим стартовый словарь
            object_counts = {'person': 0, 'car': 0, 'truck': 0}

            # Проверим, что на кадре обнаружено хоть что-то и добавим это в словарь
            if len(array_detection) > 0:
                for obj in array_detection:
                    name = obj['name']
                    object_counts[name] += 1
                    names_with_coords[f"{name}_{object_counts[name]}.jpg"] = tuple(obj['box_points'])

            # Вот так мы проверяем, что появилось новое существо на кадре
            if object_counts['person'] > old_objects_count['person'] or \
                    object_counts['car'] > old_objects_count['car'] or \
                    object_counts['truck'] > old_objects_count['truck']:

                # HERE IS NEW CODE!

                # Данные мы хотим не просто получать, но и проанализировать, спустя время.
                # Для этого будем писать логи в CSV файл. Мини БД такая, зато локальная. В нашем случае, это - плюс
                # Откроем заранее созданный, с проименованными колонками, файл CSV
                with open("date.csv", "a") as date_csv:

                    # Создадим писателя
                    writer = csv.writer(date_csv, lineterminator="\r")

                    # Передадим в переменную текущую дату и время
                    now = datetime.datetime.now()

                    # Это содержимой нашей будущей строки
                    date = now.strftime('%Y-%m-%d') # Дата
                    now_time = now.strftime('%H:%M:%S') # Время
                    person = object_counts['person'] - old_objects_count['person'] # Количество новых уникальных людей
                    car = object_counts['car'] - old_objects_count['car'] # Количество новых уникальных машин
                    truck = object_counts['truck'] - old_objects_count['truck'] # Количество новых уникальных грузовиков

                    # Сохраним все это в список и запишем в файл
                    row = [date, now_time, person, car, truck]
                    writer.writerow(row)

                # Создадим пустую стоку, куда будем записывать НЕ нулевые значения
                detection_result = ''

                for key, value in object_counts.items():
                    if value > 0:
                        detection_result += f'{key}: {value}\n'

                # И отправляем результат детекции в наш телеграм
                # bot.send_message(chat_id=CHAT_ID, text='==========================')
                bot.send_message(chat_id=CHAT_ID, text=detection_result)

                # Сохраняем вырезанные полигоны объектов и тут же отправляем их в телегу
                for name, coord in names_with_coords.items():
                    im = Image.fromarray(frame)
                    im_crop = im.crop(coord)
                    im_crop.save(f"images/{name}")

                    bot.send_photo(chat_id=CHAT_ID, photo=open(f"images/{name}", 'rb'))

            # Теперь отчистим папку с изображениями
            for file in os.listdir('images'):
                os.remove(f"images/{file}")

            # И, наконец, заполним словарь, в которым будут данные за эту итерацию. С ним мы будем сравнивать следующую
            old_objects_count = copy.deepcopy(object_counts)


# Создадим функцию запуска
def running():
    # Все файлы и папки директории
    listdir = [f for f in os.listdir()]

    # Проверим наличие файла конфигураций.
    if '.env' not in listdir:

        # Узнаем какую камеру подключать
        print('\n====================================================================\n')
        print("Hello! I see you are new! I am a Camera Watcher!")
        print("OK! Let's set up you camera!")
        print("Enter which camera do you want to use?\n1 - Local Camera\n2 - IP Camera")
        cam_type = input(": ")

        # Если локальная, то узнаем количество
        if cam_type == '1':
            cam_count = input("How many cameras do you have now?: ")

            # Если одна, то все просто
            if cam_count == '1':
                user_cam = 0

            # Если несколько, все чуть сложнее
            elif int(cam_count) > 1:
                print("You see your cameras. Press 'q' to close camera window.")

                # Попробуем подключиться к каждой камере по порядку и вывести изображение пользователю
                for camera_number in range(int(cam_count)):

                    cap = cv2.VideoCapture(camera_number)

                    while True:
                        ret, frame = cap.read()
                        try:
                            cv2.imshow(f'{camera_number}', frame)
                        except cv2.error:
                            print(f'Camera {camera_number} do not found!')
                            break

                        if cv2.waitKey(1) & 0xFF == ord('q'):
                            break

                    cap.release()
                    cv2.destroyAllWindows()

                # Тут пользователь должен выбрать с какой камерой будем работать дальше
                user_cam = input("Please, enter desired camera number: ")

            # Остальные случаи
            elif cam_count == '0':
                print("And what do you want???")
            else:
                print("Incorrect input... Please try again later...")

        # С айпи камерой все еще впереди...
        elif cam_type == '2':
            user_cam = input('Enter your IP Camera link: ')

        # Обработаем некорректный ввод
        else:
            print("Incorrect input... Please try again later...")

        # Теперь узнаем желаемую чувствительно и частоту обновления
        probability = input("Enter the probability of Camera Detection in percents: ")
        frequency = input("Enter your desired detection frequency in seconds: ")

        # Принимаем нужные нам токены.
        token = input('Your Telegram Token: ')
        chat_id = input('Your Telegram Chat ID: ')

        # Сохраняем пока что в файл конфигураций.
        lines = "\n".join([f"TOKEN={token}", f"CHAT_ID={chat_id}", f"CAMERA={user_cam}",
                           f"PROBABILITY={probability}", f"FREQUENCY={frequency}"])

        with open('.env', 'w') as f:
            f.writelines(lines)

    # Создадим поддиректорию 'images', если ее еще нет
    if 'images' not in listdir:
        os.mkdir('images')

    # Ну и, конечно, дадим возможность пользователю вносить изменения в будущем
    print('\n====================================================================\n')
    res = input('IF YOU WANT TO MAKE CHANGES IN CURRENT SETTING TYPE "X": ')

    # Если пользователь ввел "x" (икс), то вносим изменения (удаляем файл конфигураций и создаем заново
    if res.lower() == 'x':
        # Защита от дурака
        warning = input('WARNING! Your data will be PIZDEC! Are you cure want to delete them? > (Y/n)? < ')
        if warning.lower() == "y":
            os.remove('.env')
            print('Settings were delete!')
            print('Restarting...')
            running()
        else:
            print('OK!')
            garage_detection()

    # Если же любой другой символ, продолжаем с существующими настройками
    else:
        garage_detection()


def main():
    running()


if __name__ == "__main__":
    main()
