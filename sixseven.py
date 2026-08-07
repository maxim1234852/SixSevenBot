import cv2
import serial
import time

# 1. Загрузка модуля MediaPipe
try:
    from mediapipe.python.solutions import hands as mp_hands
    from mediapipe.python.solutions import drawing_utils as mp_drawing
    print("Классический модуль MediaPipe успешно загружен!")
    print("Бурмалда by Anatoly \n " * 67)
except ImportError:
    import mediapipe as mp
    mp_hands = mp.solutions.hands
    mp_drawing = mp.solutions.drawing_utils

# 2. Настройка Serial соединения с Arduino
try:
    arduino = serial.Serial(port='COM8', baudrate=9600, timeout=0.1)
    time.sleep(2) # Ожидаем инициализацию платы после сброса
    print("Соединение с Arduino установлено!")
except Exception as e:
    print(f"Ошибка подключения к Arduino: {e}")
    arduino = None

# Инициализация детектора рук
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=2,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.5
)

# Открытие веб-камеры
cap = cv2.VideoCapture(0)

# Переменные текущего состояния сервоприводов
state_servo6 = 100  # Правая рука (по умолчанию внизу = 100)
state_servo7 = 0    # Левая рука (по умолчанию внизу = 0)

print("\nКамера запущена успешно! Наведите камеру на себя.")
print("Линия триггера отображается на экране. Нажмите 'q' для выхода.\n")

while cap.isOpened():
    success, image = cap.read()
    if not success:
        print("Не удалось получить кадр с камеры.")
        continue

    # Зеркально отражаем кадр для естественного отображения (как в зеркале)
    image = cv2.flip(image, 1)
    
    # Конвертируем BGR в RGB для MediaPipe
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = hands.process(image_rgb)

    right_hand_up = False
    left_hand_up = False

    if results.multi_hand_landmarks and results.multi_handedness:
        for hand_landmarks, hand_info in zip(results.multi_hand_landmarks, results.multi_handedness):
            
            # Извлекаем тип руки, который определил MediaPipe ('Left' или 'Right')
            mp_label = hand_info.classification[0].label
            
            # КОРРЕКЦИЯ ЗЕРКАЛЬНОСТИ ДЛЯ КАМЕРЫ:
            if mp_label == 'Left':
                hand_label = 'Right'
            else:
                hand_label = 'Left'
            
            # Извлекаем координату Y запястья (WRIST).
            wrist_y = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST].y

            # ПОРОГ ТРИГГЕРА: Если рука поднята выше линии 0.45
            if wrist_y < 0.45:
                if hand_label == 'Right':
                    right_hand_up = True
                elif hand_label == 'Left':
                    left_hand_up = True

            # Отрисовка скелета руки на экране
            mp_drawing.draw_landmarks(image, hand_landmarks, mp_hands.HAND_CONNECTIONS)

    # Управление Серво 6 (Правая рука): при руке внизу -> 100, при руке вверх -> 0
    new_servo6 = 0 if right_hand_up else 100
    if new_servo6 != state_servo6:
        state_servo6 = new_servo6
        if arduino and arduino.is_open:
            arduino.write(f"6:{state_servo6}\n".encode())
            print(f"[ОТПРАВКА] Серво 6 (Правая) -> {state_servo6}")
            print("Бурмалда by Anatoly" )
        else:
            print(f"[БЕЗ ПЛАТЫ] Имитация: Серво 6 -> {state_servo6}")
            print("Бурмалда by Anatoly" )

    # ИСПРАВЛЕННОЕ УПРАВЛЕНИЕ СЕРВО 7 (Левая рука): 
    # Если при 100 она только чуть приподнималась, увеличиваем угол ВВЕРХ до 180 (или 150)
    new_servo7 = 160 if left_hand_up else 0  # Попробуйте 160 или 180 вместо 100
    if new_servo7 != state_servo7:
        state_servo7 = new_servo7
        if arduino and arduino.is_open:
            arduino.write(f"7:{state_servo7}\n".encode())
            print(f"[ОТПРАВКА] Серво 7 (Левая)  -> {state_servo7}")
            print("Бурмалда by Anatoly" )
        else:
            print(f"[БЕЗ ПЛАТЫ] Имитация: Серво 7 -> {state_servo7}")
            print("Бурмалда by Anatoly" )

    # Отрисовка текста со статусами на экране
    cv2.putText(image, f"Right Hand (Servo6): {'UP (0)' if state_servo6 == 0 else 'DOWN (100)'}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    cv2.putText(image, f"Left Hand (Servo7): {f'UP ({state_servo7})' if state_servo7 > 0 else 'DOWN (0)'}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    # Отрисовка красной линии триггера (высота 45% от верха кадра)
    h, w, _ = image.shape
    cv2.line(image, (0, int(h * 0.45)), (w, int(h * 0.45)), (0, 0, 255), 2)

    # Показ окна видео
    cv2.imshow('Hand Tracking Control', image)

    # Выход при нажатии на клавишу 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Освобождение ресурсов
cap.release()
cv2.destroyAllWindows()
if arduino:
    arduino.close()
print("Программа завершена.")
