import krpc
import time
import os
from datetime import datetime


class DualLogger:
    """Класс для одновременного вывода в консоль и файл"""

    def __init__(self, filename="ksp.txt"):
        self.filename = filename
        # Очищаем файл при запуске или создаем новый
        with open(self.filename, 'w', encoding='utf-8') as f:
            f.write(f"=== ЛОГ АВТОПИЛОТА KSP ===\n")
            f.write(f"Дата запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 40 + "\n\n")

    def log(self, message, show_time=True):
        """Записывает сообщение в файл и выводит в консоль"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        if show_time:
            log_message = f"[{timestamp}] {message}"
        else:
            log_message = message

        # Вывод в консоль
        print(log_message)

        # Запись в файл
        with open(self.filename, 'a', encoding='utf-8') as f:
            f.write(log_message + "\n")

    def section(self, title):
        """Заголовок раздела"""
        border = "=" * 50
        self.log(border, False)
        self.log(title.upper(), False)
        self.log(border, False)


class FlightDataLogger:
    """Класс для постоянной записи данных о полете в файл inf.txt"""
    
    def __init__(self, vessel, conn):
        self.vessel = vessel
        self.conn = conn
        self.filename = "inf.txt"
        self.start_time = time.time()
        
        # Настройка потоков данных
        self.altitude_stream = conn.add_stream(getattr, vessel.flight(), 'mean_altitude')
        self.apoapsis_stream = conn.add_stream(getattr, vessel.orbit, 'apoapsis_altitude')
        self.periapsis_stream = conn.add_stream(getattr, vessel.orbit, 'periapsis_altitude')
        
        # Создаем референсный фрейм для скорости
        self.body = vessel.orbit.body
        self.flight = vessel.flight(self.body.reference_frame)
        self.vertical_speed_stream = conn.add_stream(getattr, self.flight, 'vertical_speed')
        self.horizontal_speed_stream = conn.add_stream(getattr, self.flight, 'horizontal_speed')
        
        # Полная скорость
        self.speed_stream = conn.add_stream(getattr, self.flight, 'speed')
        
        # Направление (траектория)
        self.pitch_stream = conn.add_stream(getattr, self.flight, 'pitch')
        self.heading_stream = conn.add_stream(getattr, self.flight, 'heading')
        
        # Инициализация файла
        self._init_file()
        
    def _init_file(self):
        """Инициализация файла с заголовками"""
        with open(self.filename, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write("ДАННЫЕ О ПОЛЕТЕ - ПОСТОЯННАЯ ЗАПИСЬ\n")
            f.write(f"Начало записи: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Корабль: {self.vessel.name}\n")
            f.write(f"Планета: {self.body.name}\n")
            f.write("=" * 60 + "\n\n")
            
            # Заголовки столбцов
            headers = [
                "Время(с)",
                "Высота(км)",
                "Скорость(м/с)",
                "Верт.скорость(м/с)",
                "Гор.скорость(м/с)",
                "Апоапсис(км)",
                "Периапсис(км)",
                "Тангаж(°)",
                "Курс(°)",
                "Топливо",
                "Окислитель"
            ]
            f.write(" | ".join(headers) + "\n")
            f.write("-" * 120 + "\n")
    
    def log_data(self):
        """Запись текущих данных полета в файл"""
        try:
            # Получаем текущие значения
            current_time = time.time() - self.start_time
            altitude = self.altitude_stream()
            speed = self.speed_stream()
            v_speed = self.vertical_speed_stream()
            h_speed = self.horizontal_speed_stream()
            apoapsis = self.apoapsis_stream()
            periapsis = self.periapsis_stream()
            pitch = self.pitch_stream()
            heading = self.heading_stream()
            
            # Получаем ресурсы
            fuel = self.vessel.resources.amount('LiquidFuel')
            oxidizer = self.vessel.resources.amount('Oxidizer')
            
            # Форматируем строку данных
            data_line = [
                f"{current_time:6.1f}",
                f"{altitude/1000:8.2f}",
                f"{speed:8.1f}",
                f"{v_speed:8.1f}",
                f"{h_speed:8.1f}",
                f"{apoapsis/1000:8.2f}",
                f"{periapsis/1000:8.2f}",
                f"{pitch:8.1f}",
                f"{heading:8.1f}",
                f"{fuel:8.1f}",
                f"{oxidizer:8.1f}"
            ]
            
            # Записываем в файл
            with open(self.filename, 'a', encoding='utf-8') as f:
                f.write(" | ".join(data_line) + "\n")
                
        except Exception as e:
            print(f"Ошибка записи данных: {e}")
    
    def log_status(self, status):
        """Запись статуса миссии в файл"""
        with open(self.filename, 'a', encoding='utf-8') as f:
            f.write(f"\n[{datetime.now().strftime('%H:%M:%S')}] {status}\n")
    
    def close(self):
        """Завершение записи и добавление итогов"""
        elapsed_time = time.time() - self.start_time
        with open(self.filename, 'a', encoding='utf-8') as f:
            f.write("\n" + "=" * 60 + "\n")
            f.write("ИТОГИ ЗАПИСИ\n")
            f.write(f"Общее время полета: {elapsed_time:.1f} секунд\n")
            f.write(f"Конец записи: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 60 + "\n")


def get_fuel(vessel):
    """Функция для получения количества топлива"""
    try:
        return vessel.resources.amount('LiquidFuel')
    except:
        return 0


def get_oxidizer(vessel):
    """Функция для получения количества окислителя"""
    try:
        return vessel.resources.amount('Oxidizer')
    except:
        return 0


def main():
    logger = DualLogger("ksp.txt")
    flight_data_logger = None  # Инициализация позже

    logger.log("=" * 50, False)
    logger.log("AUTOPILOT FOR KSP", False)
    logger.log("=" * 50, False)
    logger.log(f"Файл лога: {os.path.abspath('ksp.txt')}")
    logger.log(f"Файл данных полета: {os.path.abspath('inf.txt')}")

    # Подключение к KSP
    try:
        logger.log("Подключаюсь к KSP через kRPC...")
        conn = krpc.connect(
            name='KSP_Autopilot',
            address='localhost',
            rpc_port=50000,
            stream_port=50001
        )
        logger.log("✓ Успешное подключение к KSP!")
    except Exception as e:
        logger.log(f"✗ Ошибка подключения: {e}")
        logger.log("Убедитесь, что:")
        logger.log("1. KSP запущена")
        logger.log("2. kRPC сервер активен (Esc → Settings → kRPC → Start Server)")
        input("Нажмите Enter для выхода...")
        return

    # Основные объекты
    vessel = conn.space_center.active_vessel
    body = vessel.orbit.body

    # Инициализация логгера данных полета
    try:
        flight_data_logger = FlightDataLogger(vessel, conn)
        logger.log("✓ Инициализирован сбор данных полета в inf.txt")
    except Exception as e:
        logger.log(f"⚠ Ошибка инициализации логгера данных: {e}")

    # Настройка потоков данных (без лямбд)
    altitude = conn.add_stream(getattr, vessel.flight(), 'mean_altitude')
    apoapsis = conn.add_stream(getattr, vessel.orbit, 'apoapsis_altitude')
    periapsis = conn.add_stream(getattr, vessel.orbit, 'periapsis_altitude')

    # Для топлива будем использовать прямые вызовы, а не потоки
    # Из-за ошибки в kRPC с лямбда-функциями

    flight = vessel.flight(body.reference_frame)
    vertical_speed = conn.add_stream(getattr, flight, 'vertical_speed')
    horizontal_speed = conn.add_stream(getattr, flight, 'horizontal_speed')

    # Информация о корабле
    logger.section("Информация о корабле")
    logger.log(f"Корабль: {vessel.name}")
    logger.log(f"Планета: {body.name}")

    # Получаем начальные значения топлива
    initial_fuel = vessel.resources.amount('LiquidFuel')
    max_fuel = vessel.resources.max('LiquidFuel')
    initial_ox = vessel.resources.amount('Oxidizer')
    max_ox = vessel.resources.max('Oxidizer')

    logger.log(f"Начальное топливо: {initial_fuel:.1f} / {max_fuel:.1f}")
    logger.log(f"Окислитель: {initial_ox:.1f} / {max_ox:.1f}")

    # Запись начального статуса в файл данных
    if flight_data_logger:
        flight_data_logger.log_status("СТАРТ МИССИИ - РАКЕТА НА СТАРТОВОЙ ПЛОЩАДКЕ")

    input("\nНажмите Enter для начала автопилота... (убедитесь, что ракета на старте!)")

    # === 1. Включить двигатель на полную ===
    logger.section("Фаза 1: Запуск двигателя")
    logger.log("1. ВКЛЮЧАЮ ДВИГАТЕЛЬ НА ПОЛНУЮ")

    # Обратный отсчет
    for i in range(3, 0, -1):
        logger.log(f"Запуск через {i}...")
        time.sleep(1)

    logger.log("ЗАПУСК! Полный газ!")
    vessel.control.throttle = 1.0
    vessel.control.activate_next_stage()
    
    # Запись статуса запуска
    if flight_data_logger:
        flight_data_logger.log_status("ЗАПУСК ДВИГАТЕЛЯ - ПОЛНЫЙ ГАЗ")
    
    time.sleep(1)

    # === 2. Включить SAS направление радиально наружу ===
    logger.log("2. ВКЛЮЧАЮ SAS: RADIAL OUT")
    vessel.control.sas = True
    time.sleep(0.5)
    try:
        vessel.control.sas_mode = conn.space_center.SASMode.radial
        logger.log("✓ SAS установлен в режим RadialOut")
    except Exception as e:
        logger.log(f"⚠ SAS radial недоступен: {e}")

    # === 3. На 10км отключить SAS и повернуть на 20° ===
    logger.section("Фаза 2: Гравитационный поворот")
    logger.log("3. ОЖИДАНИЕ ВЫСОТЫ 10 КМ...")

    last_report = time.time()
    last_data_log = time.time()
    while altitude() < 10000:
        current_time = time.time()
        
        # Запись данных каждые 0.5 секунды
        if current_time - last_data_log > 0.5 and flight_data_logger:
            flight_data_logger.log_data()
            last_data_log = current_time
        
        if current_time - last_report > 2:
            # Получаем текущие значения
            current_fuel = vessel.resources.amount('LiquidFuel')
            logger.log(f"  Высота: {altitude() / 1000:.1f} км | "
                       f"V: {vertical_speed():.0f} м/с | "
                       f"H: {horizontal_speed():.0f} м/с | "
                       f"Топливо: {current_fuel:.0f}")
            last_report = current_time
        time.sleep(0.1)

    logger.log(f"✓ 10 км достигнуто ({altitude() / 1000:.1f} км)")
    logger.log("  Отключаю SAS, поворачиваю на 20°")
    
    if flight_data_logger:
        flight_data_logger.log_status("ДОСТИГНУТО 10 КМ - ГРАВИТАЦИОННЫЙ ПОВОРОТ")

    vessel.control.sas = False
    time.sleep(0.5)

    ap = vessel.auto_pilot
    ap.reference_frame = vessel.surface_reference_frame
    ap.engage()
    ap.target_pitch_and_heading(70, 90)  # 90-20=70°
    ap.wait()
    ap.disengage()
    logger.log("  ✓ Поворот на 20° завершен")

    # === 4. Не выключать двигатель, пока апоапсис не будет 80 км ===
    logger.section("Фаза 3: Выведение до апоапсиса 80 км")
    logger.log("4. ОЖИДАНИЕ АПОАПСИСА 80 КМ...")

    last_report = time.time()
    fuel_warnings = 0
    target_pitch = vessel.flight().pitch
    
    while apoapsis() < 80000:
        
        # Запись данных каждые 0.5 секунды
        current_time = time.time()
        if current_time - last_data_log > 0.5 and flight_data_logger:
            flight_data_logger.log_data()
            last_data_log = current_time
        
        if vessel.flight().pitch > 15:
            ap.engage()
            target_pitch -= 0.3
            ap.target_pitch_and_heading(target_pitch, vessel.flight().heading)
            logger.log(f"Плавный поворот {vessel.flight().pitch}")
        
        current_apo = apoapsis()
        current_fuel = vessel.resources.amount('LiquidFuel')
        current_time = time.time()

        # Отчет каждые 3 секунды
        if current_time - last_report > 3:
            progress = (current_apo / 80000) * 100
            logger.log(f"  Апоапсис: {current_apo / 1000:.1f} км ({progress:.0f}%) | "
                       f"Высота: {altitude() / 1000:.1f} км | "
                       f"Топливо: {current_fuel:.0f}")
            last_report = current_time

        # Предупреждения о топливе
        if current_fuel < 100 and fuel_warnings == 0:
            logger.log(f"  ⚠ Мало топлива: {current_fuel:.0f} осталось")
            fuel_warnings += 1
        elif current_fuel < 50 and fuel_warnings == 1:
            logger.log(f"  ⚠ Очень мало топлива: {current_fuel:.0f} осталось")
            fuel_warnings += 1

        time.sleep(0.2)

    logger.log(f"✓ Апоапсис {apoapsis() / 1000:.1f} км достигнут")
    logger.log("  ВЫКЛЮЧАЮ ДВИГАТЕЛЬ")
    vessel.control.throttle = 0.0
    ap.disengage()
    
    if flight_data_logger:
        flight_data_logger.log_status(f"ДОСТИГНУТ АПОАПСИС {apoapsis()/1000:.1f} КМ - ВЫКЛЮЧЕНИЕ ДВИГАТЕЛЯ")

    # Сохраняем данные после первой фазы
    fuel_after_ascent = vessel.resources.amount('LiquidFuel')
    oxidizer_after_ascent = vessel.resources.amount('Oxidizer')
    logger.log(f"  Осталось после набора высоты:")
    logger.log(f"    Топливо: {fuel_after_ascent:.1f}")
    logger.log(f"    Окислитель: {oxidizer_after_ascent:.1f}")

    # === 5. Развернуть солнечные панели ===
    logger.section("Фаза 4: Развертывание систем")
    logger.log("5. РАЗВОРАЧИВАЮ СОЛНЕЧНЫЕ ПАНЕЛИ")
    
    if flight_data_logger:
        flight_data_logger.log_status("РАЗВЕРТЫВАНИЕ СОЛНЕЧНЫХ ПАНЕЛЕЙ")

    solar_count = 0
    for panel in vessel.parts.solar_panels:
        try:
            if panel.deployable:
                panel.deployed = True
                solar_count += 1
        except Exception as e:
            logger.log(f"  ⚠ Ошибка с панелью: {e}")

    if solar_count > 0:
        logger.log(f"  ✓ Развернуто солнечных панелей: {solar_count}")
    else:
        logger.log("  ⚠ Солнечные панели не найдены")

    # === 6. Дождаться высоты ~80 км ===
    logger.section("Фаза 5: Ожидание апоапсиса")
    logger.log("6. ОЖИДАНИЕ ВЫСОТЫ ~80 КМ...")
    
    if flight_data_logger:
        flight_data_logger.log_status("ОЖИДАНИЕ АПОАПСИСА 80 КМ")

    while altitude() < 78000:
        # Запись данных каждые 1 секунду (реже, так как корабль в невесомости)
        current_time = time.time()
        if current_time - last_data_log > 1.0 and flight_data_logger:
            flight_data_logger.log_data()
            last_data_log = current_time
            
        remaining = 78000 - altitude()
        if remaining < 5000:
            current_fuel = vessel.resources.amount('LiquidFuel')
            logger.log(f"  До цели: {remaining / 1000:.1f} км | "
                       f"Текущая высота: {altitude() / 1000:.1f} км | "
                       f"Топливо: {current_fuel:.1f}")
        time.sleep(0.5)

    logger.log(f"✓ Высота {altitude() / 1000:.1f} км достигнута")

    # === 7. SAS по направлению движения и жечь до периапсиса 75 км ===
    logger.section("Фаза 6: Орбитальный маневр")
    logger.log("7. ПОДГОТОВКА К ОРБИТАЛЬНОМУ МАНЕВРУ")
    
    if flight_data_logger:
        flight_data_logger.log_status("НАЧАЛО ОРБИТАЛЬНОГО МАНЕВРА")

    logger.log("  Устанавливаю SAS: Prograde")
    vessel.control.sas = True
    time.sleep(0.5)
    try:
        vessel.control.sas_mode = conn.space_center.SASMode.prograde
        logger.log("  ✓ SAS установлен в режим Prograde")
    except Exception as e:
        logger.log(f"  ⚠ SAS prograde недоступен: {e}")

    logger.log("  ВКЛЮЧАЮ ДВИГАТЕЛЬ")
    vessel.control.throttle = 1.0
    
    if flight_data_logger:
        flight_data_logger.log_status("ВКЛЮЧЕНИЕ ДВИГАТЕЛЯ ДЛЯ ОРБИТАЛЬНОГО МАНЕВРА")

    # Получаем начальные значения для маневра
    maneuver_start_fuel = vessel.resources.amount('LiquidFuel')
    maneuver_start_time = time.time()

    logger.log(f"  Цель: периапсис 75 км (текущий: {periapsis() / 1000:.1f} км)")
    logger.log(f"  Начальный запас топлива: {maneuver_start_fuel:.1f}")

    # Мониторинг маневра
    last_report = time.time()
    fuel_empty = False

    while periapsis() < 75000:
        # Запись данных каждые 0.3 секунды (часто, так как это активный маневр)
        current_time = time.time()
        if current_time - last_data_log > 0.3 and flight_data_logger:
            flight_data_logger.log_data()
            last_data_log = current_time
            
        current_fuel = vessel.resources.amount('LiquidFuel')
        current_oxidizer = vessel.resources.amount('Oxidizer')
        current_time = time.time()

        # Проверка топлива
        if current_fuel <= 0.1 or current_oxidizer <= 0.1:
            logger.log("  ✗ ТОПЛИВО КОНЧИЛОСЬ!")
            fuel_empty = True
            break

        # Отчет каждые 2 секунды
        if current_time - last_report > 2:
            fuel_used = maneuver_start_fuel - current_fuel
            time_elapsed = current_time - maneuver_start_time
            progress = (periapsis() / 75000) * 100 if periapsis() > 0 else 0

            logger.log(f"  Периапсис: {periapsis() / 1000:.1f} км ({progress:.0f}%) | "
                       f"Топливо: {current_fuel:.1f} | "
                       f"Использовано: {fuel_used:.1f} | "
                       f"Время: {time_elapsed:.0f}с")
            last_report = current_time

        time.sleep(0.2)

    # Выключаем двигатель в любом случае
    vessel.control.throttle = 0.0
    logger.log("  Двигатель выключен")
    
    if flight_data_logger:
        flight_data_logger.log_status(f"ЗАВЕРШЕНИЕ МАНЕВРА - ПЕРИАПСИС {periapsis()/1000:.1f} КМ")

    # === ИТОГИ ===
    logger.section("Результаты миссии")

    final_apo = apoapsis()
    final_peri = periapsis()
    final_fuel = vessel.resources.amount('LiquidFuel')
    final_ox = vessel.resources.amount('Oxidizer')

    logger.log("ПАРАМЕТРЫ ОРБИТЫ:")
    logger.log(f"  Апоапсис: {final_apo / 1000:.2f} км")
    logger.log(f"  Периапсис: {final_peri / 1000:.2f} км")

    try:
        eccentricity = vessel.orbit.eccentricity
        logger.log(f"  Эксцентриситет: {eccentricity:.4f}")
    except:
        logger.log("  Эксцентриситет: недоступен")

    logger.log("\nОСТАТОК РЕСУРСОВ:")
    logger.log(f"  Топливо: {final_fuel:.1f}")
    logger.log(f"  Окислитель: {final_ox:.1f}")

    logger.log("\nСТАТИСТИКА ПОЛЕТА:")
    logger.log(f"  Топливо израсходовано на маневр: {maneuver_start_fuel - final_fuel:.1f}")
    logger.log(f"  Общее время маневра: {time.time() - maneuver_start_time:.1f}с")

    # Анализ результата
    logger.log("\nАНАЛИЗ РЕЗУЛЬТАТА:")

    if fuel_empty:
        logger.log("✗ НЕУДАЧА: Топливо закончилось до завершения маневра")
        if final_peri > 0:
            logger.log(f"  Достигнута высота периапсиса: {final_peri / 1000:.1f} км")
            logger.log("  Рекомендация: Увеличить запас топлива или уменьшить целевую орбиту")
        else:
            logger.log("  Суборбитальная траектория - периапсис под поверхностью")
            logger.log("  Критическая ошибка: недостаточно топлива для выхода на орбиту")
    elif final_peri >= 70000:
        logger.log("✓ УСПЕХ: Орбита достигнута!")
        if final_peri >= 74000 and final_peri <= 76000:
            logger.log("  Отличная точность! Орбита в целевом диапазоне")
        else:
            logger.log(f"  Орбита стабильная, но не идеальная ({final_peri / 1000:.1f} км)")
    elif final_peri > 0:
        logger.log("⚠ Частичный успех: Субоптимальная орбита")
        logger.log(f"  Периапсис {final_peri / 1000:.1f} км - требует корректировки")
    else:
        logger.log("✗ КРИТИЧЕСКАЯ НЕУДАЧА: Суборбитальная траектория")
        logger.log("  Ракета упадет на поверхность")
        logger.log("  Необходимо полностью пересмотреть конструкцию или профиль полета")

    # Завершение записи данных полета
    if flight_data_logger:
        flight_data_logger.log_status("ЗАВЕРШЕНИЕ МИССИИ")
        flight_data_logger.close()
        logger.log(f"\n✓ Данные полета сохранены в: {os.path.abspath('inf.txt')}")

    # Закрываем соединение
    conn.close()

    logger.log("\n" + "=" * 50, False)
    logger.log(f"Лог событий: {os.path.abspath('ksp.txt')}", False)
    logger.log(f"Данные полета: {os.path.abspath('inf.txt')}", False)
    logger.log("=" * 50, False)

    input("\nНажмите Enter для завершения...")


if __name__ == '__main__':
    main()

