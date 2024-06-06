import psycopg2

def connect_to_database():
    """
    Подключение к базе данных.

    Returns:
        psycopg2.extensions.connection: Соединение с базой данных, если успешно, иначе None.
    """
    try:
        conn = psycopg2.connect(
            dbname="postgres",
            user="postgres",
            password="vadim220702",
            host="localhost",
            port="5432"
        )
        print("Подключение установлено")
        return conn
    except psycopg2.Error as e:
        print("Ошибка подключения к базе данных:", e)
        return None

def execute_query(conn, query):
    """
    Выполнение SQL-запроса.

    Args:
        conn: Соединение с базой данных.
        query (str): SQL-запрос для выполнения.

    Returns:
        list or None: Результат выполнения запроса (если есть), иначе None.
    """
    try:
        cur = conn.cursor()
        cur.execute(query)
        rows = cur.fetchall()
        cur.close()
        return rows
    except psycopg2.Error as e:
        print("Ошибка выполнения запроса:", e)
        return None

def close_connection(conn):
    """
    Закрытие соединения с базой данных.

    Args:
        conn: Соединение с базой данных.

    Returns:
        None
    """
    if conn is not None:
        conn.close()
        print("Соединение с базой данных закрыто.")

def insert_service(conn, uri, token, name, category_id, image, description):
    """
    Вставляет новый сервис в таблицу services.service и возвращает его идентификатор (ID).

    Args:
        conn: Соединение с базой данных.
        uri: URI нового сервиса.
        token: Токен нового сервиса.
        name: Название нового сервиса.
        category_id: ID категории нового сервиса.
        image: Путь до логотипа сервиса
        description: Описание сервиса

    Returns:
        int: Идентификатор (ID) только что добавленного сервиса, или None в случае ошибки.
    """
    # Проверка наличия соединения с базой данных
    if not conn:
        print("Отсутствует соединение с базой данных.")
        return None

    try:
        # Проверка наличия URI в базе данных
        query = "SELECT uri FROM services.service WHERE uri = %s;"
        cur = conn.cursor()
        cur.execute(query, (uri,))
        existing_uri = cur.fetchone()

        if existing_uri:
            print("URI уже существует в базе данных.")
            return None

        # Вставка нового сервиса
        insert_query = """
            INSERT INTO services.service (uri, "token", "name", category_id, logo, description, api_source)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
        """
        cur.execute(insert_query, (uri, token, name, category_id, image, description, "RapidAPI"))
        conn.commit()
        inserted_id = cur.fetchone()[0]
        print("Данные успешно добавлены в таблицу services.service.")
        return inserted_id
    except psycopg2.Error as e:
        conn.rollback()
        print("Ошибка при добавлении данных в таблицу services.service:", e)
        return None
def insert_endpoint(conn, service_id, name, description):
    """
    Вставляет новую конечную точку (endpoint) в таблицу service_points и возвращает ее идентификатор (ID).

    Args:
        conn: Соединение с базой данных.
        service_id: Идентификатор сервиса.
        name: Название конечной точки.
        description: Описание конечной точки.

    Returns:
        int or None: Идентификатор (ID) только что добавленной конечной точки, или None в случае ошибки.
    """
    try:
        # Устанавливаем соединение с базой данных
        cursor = conn.cursor()

        # Выполняем SQL-запрос для вставки данных в таблицу service_points
        cursor.execute("""
            INSERT INTO services.service_points (service_id, uri, description)
            VALUES (%s, %s, %s)
            RETURNING id;
        """, (service_id, name, description))

        # Получаем id service_points
        service_point_id = cursor.fetchone()[0]

        # Фиксируем изменения в базе данных
        conn.commit()

        # Закрываем курсор и возвращаем id service_points
        cursor.close()
        return service_point_id
    except (Exception, psycopg2.Error) as error:
        # Если возникла ошибка, откатываем транзакцию и выводим сообщение об ошибке
        if conn:
            conn.rollback()
        print("Ошибка при вставке данных:", error)
        return None


def insert_parameters(conn, service_point_id, name, description, flag, param_type):
    """
    Вставляет новый параметр в таблицу service_parameters и возвращает его идентификатор (ID).

    Args:
        conn: Соединение с базой данных.
        service_point_id: Идентификатор конечной точки, к которой привязан параметр.
        name: Название параметра.
        description: Описание параметра.
        flag: Флаг, указывающий на обязательность параметра.
        param_type: Тип параметра.

    Returns:
        int or None: Идентификатор (ID) только что добавленного параметра, или None в случае ошибки.
    """
    try:
        # Формируем jpath
        jpath = "$." + name

        # Устанавливаем соединение с базой данных
        cursor = conn.cursor()

        # Проверяем, существует ли такой тип параметра в таблице type
        cursor.execute("""
            SELECT id FROM components."type" WHERE "type" = %s;
        """, (param_type,))
        type_row = cursor.fetchone()

        if type_row:
            type_id = type_row[0]
        else:
            # Если тип параметра отсутствует, добавляем его в таблицу type
            cursor.execute("""
                INSERT INTO components."type" ("type") VALUES (%s) RETURNING id;
            """, (param_type,))
            type_id = cursor.fetchone()[0]

        # Выполняем SQL-запрос для вставки данных в таблицу service_parameters
        cursor.execute("""
            INSERT INTO services.service_parameters (service_point_id, "name", is_return_value, description, "default", jpath, required, type_id)
            VALUES (%s, %s, NULL, %s, NULL, %s, %s, %s)
            RETURNING id;
        """, (service_point_id, name, description, jpath, flag, type_id))

        # Получаем id service_parameters
        parameter_id = cursor.fetchone()[0]

        # Фиксируем изменения в базе данных
        conn.commit()

        # Закрываем курсор и возвращаем id service_parameters
        cursor.close()
        return parameter_id
    except (Exception, psycopg2.Error) as error:
        # Если возникла ошибка, откатываем транзакцию и выводим сообщение об ошибке
        if conn:
            conn.rollback()
        print("Ошибка при вставке данных:", error)
        return None
def get_categories(conn):
    """
    Получает список категорий из базы данных.

    Args:
        conn: Соединение с базой данных.

    Returns:
        list: Список кортежей (ID, название) категорий.
    """
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM services.service_categories;")
    categories = cursor.fetchall()
    cursor.close()
    return categories

def insert_category_id_to_service(conn, service_id, category_id):
    """
    Вставляет ID категории в запись о сервисе в базе данных.

    Args:
        conn: Соединение с базой данных.
        service_id: Идентификатор сервиса.
        category_id: Идентификатор категории.

    Returns:
        None
    """
    try:
        cursor = conn.cursor()

        # Выполняем SQL-запрос для обновления записи в таблице services с указанным service_id
        cursor.execute("UPDATE services.service SET category_id = %s WHERE id = %s;", (category_id, service_id))

        # Фиксируем изменения в базе данных
        conn.commit()

        # Закрываем курсор и соединение с базой данных
        cursor.close()

        print("ID категории успешно добавлено к сервису с ID: {}.".format(service_id))
    except (Exception, psycopg2.Error) as error:
        print("Ошибка при вставке данных в базу данных:", error)

