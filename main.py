from flask import Flask, render_template, request
import time
from selenium import webdriver
from selenium.common import NoSuchElementException, ElementNotInteractableException
from selenium.webdriver.common.by import By
import os
import requests
import database_operations

app = Flask(__name__)

methods_data = {}  # словарь для хранения извлеченных данных

def download_image(url, name):
    """
    Загружает изображение по указанному URL и сохраняет его на диск.

    Args:
        url (str): URL-адрес изображения для загрузки.
        name (str): Имя, под которым изображение будет сохранено.

    Returns:
        str or None: Путь к сохраненному изображению, если загрузка прошла успешно, иначе None.
    """

    image_save_path = "C:/service-collections/images"  # Путь, куда сохранить изображение
    print(name)
    save_path = os.path.join(image_save_path, f"{name}.jpg")
    response = requests.get(url)
    if response.status_code == 200:
        with open(save_path, "wb") as f:
            f.write(response.content)
        return save_path
    else:
        return None

def get_iframe_srcs(url):
    """
       Получает URL-адрес страницы и извлекает информацию об iframe логотип сервиса и описание.

       Args:
       url (str): URL-адрес страницы, с которой нужно извлечь информацию.

       Returns:
       tuple: Кортеж с URL-адресом iframe, названием сервиса и описанием.
       """

    # XPath для изображения, названия сервиса и описания
    image_xpath = "//*[@id='__layout']/div/div[2]/div/div[1]/div/header/div/div[1]/img"
    service_name_xpath = "//*[@id='__layout']/div/div[2]/div/div[1]/div/header/div/div[2]/div[1]/h2"
    description_xpath = "//*[@id='__layout']/div/div[2]/div/div[2]/header/div/div/div[1]/div"

    # Настройки для запуска браузера Chrome в фоновом режиме
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')

    # Запуск веб-драйвера Chrome
    driver = webdriver.Chrome(options=options)
    driver.get(url)
    time.sleep(10)

    # Извлечение элементов страницы
    image_element = driver.find_element(By.XPATH, image_xpath)
    service_name_element = driver.find_element(By.XPATH, service_name_xpath).text
    description_element = driver.find_element(By.XPATH, description_xpath).text

    # Получение URL-адреса изображения
    image_src = image_element.get_attribute("src")
    time.sleep(5)
    download_image(image_src, service_name_element)
    iframe = driver.find_element(By.XPATH, "//iframe[@class='PlaygroundContainer']")
    iframe_src = iframe.get_attribute("src")
    driver.quit()

    # Возвращение URL-адреса iframe, названия сервиса и описания
    return str(iframe_src), service_name_element, description_element


def getters(driver, conn, service_id):
    """
    Метод для извлечения данных с сайта.

    Parameters:
    - driver: объект драйвера Selenium для взаимодействия с веб-страницей.
    - conn: соединение с базой данных для выполнения операций записи.
    - service_id: идентификатор сервиса, к которому относятся извлекаемые данные.

    Returns:
    Словарь с информацией о методах, содержащий следующие ключи:
    - 'description': описание метода;
    - 'required_parameters': список обязательных параметров метода, каждый параметр представлен словарем с ключами 'param_name', 'type' и 'description';
    - 'Optional_parameters': список необязательных параметров метода, каждый параметр представлен словарем с ключами 'param_name', 'type' и 'description'.
    """
    method_name = (driver.find_element(By.XPATH,
                                               "/html/body/div[1]/div/div[2]/div[3]/div/div/form/div[1]/div/span[2]")).text # Находим элемент с именем метода на веб-странице и извлекаем текст

    method_description = (driver.find_element(By.XPATH,
                                                     "/html/body/div[1]/div/div[2]/div[3]/div/div/form/div[2]/div["
                                                     "1]/div[1]/div/div/div/p[1]")).text  # Находим элемент с описанием
    endpoint_id = database_operations.insert_endpoint(conn, service_id, method_name, method_description)  # Вставляем данные о методе в базу данных и получаем его идентификатор
    methods_data[method_name] = {  # Создаем запись о методе в словаре `methods_data`
        "description": method_description,
        "required_parameters": [],
        "Optional_parameters": []
    }
    try:
        required_parameter_check = driver.find_element(By.XPATH, "/html/body/div/div/div[2]/div[3]/div/div/form/div[2]/div[2]/div[2]/div[1]").text
    except NoSuchElementException:
        required_parameter_check = "" # или любое другое значение, которое указывает на отсутствие элемента
    required_flag = False
    # Скрапим обязательные параметры
    if required_parameter_check == "Required Parameters":
        i = 1  # Инициализация счетчика для обязательных параметров
        while True:
            try:
                # Извлекаем имя, тип и описание обязательного параметра
                param_name = driver.find_element(By.XPATH,
                                                 f"/html/body/div[1]/div/div[2]/div[3]/div/div/form/div[2]/div[2]/div["
                                                 f"2]/div[2]/div/div[{i}]/div[1]/label").text
                param_type = driver.find_element(By.XPATH,
                                                 f"/html/body/div[1]/div/div[2]/div[3]/div/div/form/div[2]/div[2]/div["
                                                 f"2]/div[2]/div/div[{i}]/div[1]/div[1]").text
                param_type = param_type.lower()
                param_description = driver.find_element(By.XPATH,
                                                        f"/html/body/div[1]/div/div[2]/div[3]/div/div/form/div[2]/div["
                                                        f"2]/div[2]/div[2]/div/div[{i}]/div[2]/div/div/div[2]/div/div["
                                                        f"2]/div/p").text
                database_operations.insert_parameters(conn, endpoint_id, param_name, param_description, True, param_type)   # Вставляем данные об обязательном параметре в базу данных
                methods_data[method_name]["required_parameters"].append({  # Добавляем информацию об обязательном
                    # параметре в словарь `methods_data`
                    "param_name": param_name,
                    "type": param_type,
                    "description": param_description
                })
                i += 1
                required_flag = True
            except NoSuchElementException:
                break
    # Скрапим не обязательные параметры, когда есть обязательные
    if required_flag == True:
        i = 1
        while True:
            try:
                param_name = driver.find_element(By.XPATH,
                                             f"/html/body/div/div/div[2]/div[3]/div/div/form/div[2]/div[2]/div[3]/div[2]/div/div[{i}]/div[1]/label").text
                print(param_name)
                param_type = driver.find_element(By.XPATH,
                                                 f"/html/body/div/div/div[2]/div[3]/div/div/form/div[2]/div[2]/div[3]/div[2]/div/div[{i}]/div[1]/div[1]").text
                param_type = param_type.lower()
                param_description = driver.find_element(By.XPATH,
                                                        f"/html/body/div/div/div[2]/div[3]/div/div/form/div[2]/div[2]/div[3]/div[2]/div/div[{i}]/div[2]/div/div/div[2]/div/div[2]/div").text
                database_operations.insert_parameters(conn, endpoint_id, param_name, param_description, False,
                                                      param_type)  # Вставляем данные о необязательном параметре в базу данных
                methods_data[method_name]["Optional_parameters"].append(
                    {  # Добавляем информацию о необязательном параметре в словарь `methods_data`
                        "param_name": param_name,
                        "type": param_type,
                        "description": param_description
                    })
                i += 1
            except NoSuchElementException:
                break
    # Скрапим не обязательные параметры, когда нет обязательных параметров
    else:
        i = 1
        while True:
            try:
                param_name = driver.find_element(By.XPATH,
                                                 f"/html/body/div/div/div[2]/div[3]/div/div/form/div[2]/div[2]/div[2]/div[2]/div/div[{i}]/div[1]/label").text
                param_type = driver.find_element(By.XPATH,
                                                 f"/html/body/div/div/div[2]/div[3]/div/div/form/div[2]/div[2]/div[2]/div[2]/div/div[{i}]/div[1]/div[1]").text
                param_type = param_type.lower()
                param_description = driver.find_element(By.XPATH,
                                                        f"/html/body/div/div/div[2]/div[3]/div/div/form/div[2]/div[2]/div[2]/div[2]/div/div[{i}]/div[2]/div/div/div[2]/div/div[2]/div").text
                database_operations.insert_parameters(conn, endpoint_id, param_name, param_description, False,
                                                      param_type)  # Вставляем данные о необязательном параметре в базу данных
                methods_data[method_name]["Optional_parameters"].append(
                    {  # Добавляем информацию о необязательном параметре в словарь `methods_data`
                        "param_name": param_name,
                        "type": param_type,
                        "description": param_description
                    })
                print("Optional ", param_name)

                i += 1
            except NoSuchElementException:
                break
    return methods_data  # Возвращаем словарь с информацией о методах




def click_buttons_in_divs(driver, conn, service_id):
    """
    Метод для переключения кнопок и списков на сайте.

    Args:
        driver: WebDriver объект для взаимодействия с браузером.
        conn: Объект соединения с базой данных.
        service_id: Идентификатор сервиса.

    Returns:
        None
    """
    try:
        headers = driver.find_elements(By.CLASS_NAME, "ant-collapse-header")  # Найти все элементы <div> с классом "ant-collapse-header"
        skip_first = True  # Пропустить первое вхождение в headers
        for header in headers:  # Нажать на каждый заголовок, чтобы раскрыть скрытые кнопки
            if skip_first:   # Если это первое вхождение, пропустить его
                skip_first = False
                continue
            if header.text == "Header Parameters" or header.text == "Required Parameters" or header.text == "Optional Parameters":  # Проверяем, если текст заголовка соответствует определенным значениям, пропускаем нажатие
                continue
            header.click()
        buttons = driver.find_elements(By.XPATH, "//div[@class='content']")  # После раскрытия всех кнопок, найти и нажать на кнопки внутри <div class="content">
        for button in buttons:
            button.click()
            getters(driver, conn, service_id)
        print('stage 3')
    except ElementNotInteractableException:
        # Если возникла ошибка ElementNotInteractableException, увеличьте время ожидания и повторите попытку
        time.sleep(10)
        click_buttons_in_divs(driver, conn, service_id)

def scrap_data(url, conn, selected_category, categories, service_name, description):
    """
    Функция для сбора данных.

    Args:
        url (str): URL-адрес для доступа к данным.
        conn: Объект соединения с базой данных.
        selected_category (str): Выбранная категория данных.
        categories: Список категорий.
        service_name: Имя сервиса
        description: Описание сервиса

    Returns:
        str: Сообщение об успешном выполнении или предупреждение.
    """
    print(selected_category)
    methods_data.clear()
    # Запускаем браузер Chrome с отключенным кэшированием
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')  # Включение безголового режима
    driver = webdriver.Chrome(options=options)
    try:
        driver.get(url)
        time.sleep(10)
        '''Получение URL'''
        X_RapidAPI_Host_input = driver.find_element(By.ID, "x-rapidapi-host")
        X_RapidAPI_Host = X_RapidAPI_Host_input.get_attribute("value")
        name = X_RapidAPI_Host.split(".")[0]
        service_id = database_operations.insert_service(conn, X_RapidAPI_Host, 'test', service_name, 1, service_name + '.jpg', description)
        if service_id is None:
            warning_message = "Такой сервис уже существует."
            print(warning_message)
            return warning_message
        else:
            print('stage 2')
            database_operations.insert_category_id_to_service(conn, service_id, selected_category)
            click_buttons_in_divs(driver, conn, service_id)
            time.sleep(10)
    finally:
        driver.quit()


@app.route('/', methods=['GET', 'POST'])
def index():
    """
    Главная функция для обработки запросов на главной странице.

    Returns:
        HTML: Возвращает HTML-шаблон в зависимости от запроса.
    """
    conn = database_operations.connect_to_database()  # Устанавливаем соединение с базой данных
    categories = database_operations.get_categories(conn)  # Получаем список категорий из базы данных

    if request.method == 'POST':  # Если метод запроса - POST
        selected_category_id = request.form.get('category')  # Получаем выбранную категорию из формы
        url = request.form['url']  # Получаем URL из формы
        iframe_src, service_name, description = get_iframe_srcs(url)  # Получаем источник iframe из URL
        print('stage 1')
        # Собираем данные с полученного URL
        warning_message = scrap_data(iframe_src, conn, selected_category_id, categories, service_name, description)
        if warning_message == 'Такой сервис уже существует.':  # Если сервис уже существует
            return render_template('index.html', warning=warning_message, categories=categories)  # Возвращаем предупреждение и список категорий
        else:
            return render_template('index.html', data=methods_data, categories=categories)  # Возвращаем данные и список категорий

    # Если метод запроса - GET, просто отображаем главную страницу с категориями
    return render_template('index.html', categories=categories)

if __name__ == '__main__':
    app.run(debug=False)
