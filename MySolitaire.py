from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

import os
import random

WINDOW_SIZE = 840, 600

CARD_DIMENSIONS = QSize(80, 116)
CARD_RECT = QRect(0, 0, 80, 116)
CARD_SPACING_X = 110
CARD_BACK = QImage(os.path.join("images", "back.png"))

DEAL_RECT = QRect(30, 30, 110, 140)

OFFSET_X = 50
OFFSET_Y = 50
WORK_STACK_Y = 200

SIDE_FACE = 0
SIDE_BACK = 1

BOUNCE_ENERGY = 0.8

# We store cards as numbers 1-13, since we only need
# to know their order for solitaire.
SUITS = ["C", "S", "H", "D"]


# Вспомогательный класс Signals создает и инкапсулирует в себе
# все сигналы, которые будут обрабатываться в процессе данной игры
class Signals(QObject):
    complete = pyqtSignal()
    clicked = pyqtSignal()
    doubleclicked = pyqtSignal()


# Класс Card описывает объект игральной карты
class Card(QGraphicsPixmapItem):

    def __init__(self, value, suit, *args, **kwargs):
        super(Card, self).__init__(*args, **kwargs)

# поле signals - сигналы на которые будет реагировать карта
        self.signals = Signals()

        self.stack = None
        self.child = None

# Старшинство
        self.value = value
# Масть
        self.suit = suit
        self.side = None

        self.vector = None

# Устанавливаем режим рисования области карты
        self.setShapeMode(QGraphicsPixmapItem.BoundingRectShape)
# Устанавливаем - область карты можно таскать мышкой
        self.setFlag(QGraphicsItem.ItemIsMovable)
# Устанавливаем - перемещение области карты будет генерировать события
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)

# Устанавливаем графическое изображение карты
        self.load_images()

    def load_images(self):
        self.face = QPixmap(
# Устанавливаем на лицевую сторону карты графическое изображение из файла карты
            os.path.join("cards", "%s%s.png" % (self.value, self.suit))
        )

        self.back = QPixmap(
# Устанавливаем на рубашку карты графическое изображение из файла back.png
            os.path.join("images", "back.png")
        )

# Показываем карту лицом
    def turn_face_up(self):
        self.side = SIDE_FACE
        self.setPixmap(self.face)

# Показываем карту рубашкой
    def turn_back_up(self):
        self.side = SIDE_BACK
        self.setPixmap(self.back)

# Свойство возвращает флаг открытости карты
    @property
    def is_face_up(self):
        return self.side == SIDE_FACE

# Свойство возвращает цвет масти карты
    @property
    def color(self):
        return "r" if self.suit in ("H", "D") else "b"

# Переопределение метода обработки события нажатия кнопки мышки
    def mousePressEvent(self, e):
        if not self.is_face_up and self.stack.cards[-1] == self:
# Если карта отображена рубашкой и она верхняя в колоде, тогда открываем ее
            self.turn_face_up()
# забираем из очереди событие
            e.accept()
            return

# Если карта закрыта другими картами в колоде, тогда событие игнорим
        if self.stack and not self.stack.is_free_card(self):
            e.ignore()
            return

# перевод фокуса на колоду этой карты
        self.stack.activate()

        e.accept()

        super(Card, self).mouseReleaseEvent(e)

# Переопределение метода обработки события отпускания кнопки мышки
    def mouseReleaseEvent(self, e):
# сняли фокус с колоды из которой перетащили карту
        self.stack.deactivate()

# получили спмсок областей (карт или колод) в которые перетаскивается карта
        items = self.collidingItems()
        if items:
# находим верхнюю карту из колоды в которую кидаем
            for item in items:
# если тащим одну карту в другую колоду
                if ((isinstance(item, Card) and item.stack != self.stack) or
# или если перетаскиваем несколько карт в другую колоду
                        (isinstance(item, StackBase) and item != self.stack)):

# проверка правильности переноса карты
                    if item.stack.is_valid_drop(self):
# убираем карту(ы) из колоды где она была
                        cards = self.stack.remove_card(self)
# помещаем карту(ы) в другую колоду
                        item.stack.add_cards(cards)
                        break

# обновляем колоду из которой только что убрали карту
        self.stack.update()

# сделали по события все наши дела и перекинули его предку
        super(Card, self).mouseReleaseEvent(e)

# Переопределение метода обработки события двойного клика кнопкой мышки
    def mouseDoubleClickEvent(self, e):
# если карта открыта, тогда вызываем ее сигнал doubleclicked
        if self.stack.is_free_card(self):
            self.signals.doubleclicked.emit()
            e.accept()

# отдали событие предку
        super(Card, self).mouseDoubleClickEvent(e)

# Классс StackBase описывает произвольное множество игральных карт - это базовый тип
# от которого наследуются классы - описатели различных колод
class StackBase(QGraphicsRectItem):

# Метод конструктора - действия при создании объекта
    def __init__(self, *args, **kwargs):
# Вызываем конструктор предка
        super(StackBase, self).__init__(*args, **kwargs)

# Устанавливаем прямоуольную область видимости по парометрам указанным в CARD_RECT
        self.setRect(QRectF(CARD_RECT))
# Помещаем эту область в начальный (невидимый) слой
        self.setZValue(-1)

# Поле для хранения массива карт
        self.cards = []

# Вспомогательное поле для сохранения ссылки на самого себя
        self.stack = self
        self.setup()
        self.reset()

    def setup(self):
        pass

# Метод reset очищает массив self.cards
    def reset(self):
        self.remove_all_cards()

# Метод update выполняет графическое овормление карт в массиве self.cards,
# что бы множество карт self.cards визуально представляло сложенную колоду
    def update(self):
        for n, card in enumerate(self.cards):
# карта с номером n в массиве отображается в прямоугольники, который немного (определяется offset_x, offset_y)
# сдвинут относительно прямоугольника предидущей карты n - 1.
            card.setPos( self.pos() + QPointF(n * self.offset_x, n * self.offset_y))
# карта с номером n в массиве помещается слой отображения, который выше слоя отображения карты n - 1
            card.setZValue(n)

    def activate(self):
        pass

    def deactivate(self):
        pass

# Метод add_card добавляет один объект card колоду self.cards
    def add_card(self, card, update=True):
        card.stack = self
        self.cards.append(card)
# Если требуется, то дополнительно обновляем визуальное отображение колоды
        if update:
            self.update()

# Метод add_cards добавляет множество объектов card колоду self.cards
    def add_cards(self, cards):
        for card in cards:
            self.add_card(card, update=False)
        self.update()

# Метод remove_card удаляет объект card из колоды self.cards
# и возвращает card в виде списка
    def remove_card(self, card):
# зануляем ссылку на колоду
        card.stack = None
        self.cards.remove(card)
        self.update()
        return [card]

# Метод remove_all_cards очищает массив self.cards
    def remove_all_cards(self):
        for card in self.cards[:]:
            card.stack = None
        self.cards = []

    def is_valid_drop(self, card):
        return True

    def is_free_card(self, card):
        return False

# Классс DeckStack описывает колоду карт для сдачи
class DeckStack(StackBase):

# Параметры относительного смещения карт между собой в колоде
    offset_x = -0.2
    offset_y = -0.3

# Счетчик выполненых раздач
    restack_counter = 0

# Метод reset обновляет колоду раздачи при перезапуске игры
# Вызов reset предка, обнуляем счетчик, обновляем закраску колоды
    def reset(self):
        super(DeckStack, self).reset()
        self.restack_counter = 0
        self.set_color(Qt.green)

# Метод stack_cards заполняет колоду картами из массива cards
# все карты в колоде отображаются рубашкой к верху
    def stack_cards(self, cards):
        for card in cards:
            self.add_card(card)
            card.turn_back_up()

# Метод can_restack возвращает TRUE если количество выполненных раздач
# не превысило максимально допустимое n_rounds и колода может быть перездана вновь
# иначе возвращается FALSE
    def can_restack(self, n_rounds=3):
        return n_rounds is None or self.restack_counter < n_rounds-1

# Метод update_stack_status обновляет цвет закраску 2D-области колоды
# в зависимости от ее состояния
    def update_stack_status(self, n_rounds):
        if not self.can_restack(n_rounds):
            self.set_color(Qt.red)
        else:
            self.set_color(Qt.green)

# Метод restack перемещает карты из массива dealstack (колода розданных карт) обратно в колоду раздачи
# все карты переворачиваются рубашкой к верху
    def restack(self, fromstack):
        self.restack_counter += 1

        for card in fromstack.cards[::-1]:
            fromstack.remove_card(card)
            self.add_card(card)
            card.turn_back_up()

# Метод take_top_card возвращает верхнюю карту изи колоды
    def take_top_card(self):
        try:
            card = self.cards[-1]
            self.remove_card(card)
            return card
        except IndexError:
            pass

# Закрашивание 2D-поля колоды карт
    def set_color(self, color):
# Получаем цвет закраски
        color = QColor(color)
# Устанавливаем уровень прозрачности закраски
        color.setAlpha(50)
        brush = QBrush(color)
# Закраска
        self.setBrush(brush)
# Устанавливаем отсутствие границ закрашиваемой области
        self.setPen(QPen(Qt.NoPen))

    def is_valid_drop(self, card):
        return False


# Классс DealStack описывает колоду карт уже сданных игроку
class DealStack(StackBase):

    offset_x = 20
    offset_y = 0

    spread_from = 0

# Метод setup обновляет колоду сданных карт при перезапуске игры и при перезаполнении колоды сдачи
    def setup(self):
# Устанавливаем отсутствие границ закрашиваемой области
        self.setPen(QPen(Qt.NoPen))
# Устанавливаем черный полупрозрачный цвет закраски 2D-области колоды
        color = QColor(Qt.black)
        color.setAlpha(50)
# Закраска
        brush = QBrush(color)
        self.setBrush(brush)

# Метод reset очищает колоду сданных карт
    def reset(self):
        super(DealStack, self).reset()
        self.spread_from = 0

    def is_valid_drop(self, card):
        return False

# Метод is_free_card TRUE есликолода сданных карт еще пуста
    def is_free_card(self, card):
        return card == self.cards[-1]

# Метод update перерисовывает 2D-область колоды при сдаче очередных карт
    def update(self):
        offset_x = 0
# идем по сданным картам
        for n, card in enumerate(self.cards):
# Устанавливаем положение верхней сданной карты со сдвигом вправо на величину offset_x относительно нижней
# что бы игрок увидел сданные ему карты
            card.setPos(self.pos() + QPointF(offset_x, 0))
# Устанавливаем порядок сдаваемых карт
            card.setZValue(n)

# Увеличиваем относительный сдвиг
            if n >= self.spread_from:
                offset_x = offset_x + self.offset_x


# Класс WorkStack описывает игровое поле
class WorkStack(StackBase):

    offset_x = 0
    offset_y = 15
    offset_y_back = 5

# Метод setup устанавливает затемненное цветовое оформление для каждой
# из 7 игровых колонок
    def setup(self):
        self.setPen(QPen(Qt.NoPen))
        color = QColor(Qt.black)
        color.setAlpha(50)
        brush = QBrush(color)
        self.setBrush(brush)

# Метод activate устанавливает все карты игровых колонок в слое отображения,
# который выше всех остальных слоев
    def activate(self):
        self.setZValue(1000)

# Метод deactivate перемещает все карты игровых колонок в невидимый слой (скрытие)
    def deactivate(self):
        self.setZValue(-1)

# Метод is_valid_drop проверяет, можно ли помещать карту card
    def is_valid_drop(self, card):
# Если колонка в которую перемещается card уже без карт, тогда можно
        if not self.cards:
            return True

# Если цвет масти карты card отличается от цвета масти верхней карты в колонке и
# старшинство карты card меньше старшинства верхней карты в колонке на 1, тогда можно
        if (card.color != self.cards[-1].color and
                card.value == self.cards[-1].value -1):
            return True

# Во всех остальных случаях, пермещать карту card нельзя
        return False

# Метод is_free_card проверяет, доступна ли  карта card для помещать
    def is_free_card(self, card):
# Если она отображается открытой, тогда ДА, если рубашкой тогда НЕТ
        return card.is_face_up

# Метод add_card помещает карту card на игровое поле
    def add_card(self, card, update=True):
# В колонке уже есть карта, то она назначатся владельцем (к ней привязывается) помещаемая карта card
        if self.cards:
            card.setParentItem(self.cards[-1])
        else:
# Если колонка еще пуста, то владельцем карты card назначается само игровое поле WorkStack
            card.setParentItem(self)

# Вызываем родительский метод add_card
        super(WorkStack, self).add_card(card, update=update)

# Метод remove_card из игрового поля
    def remove_card(self, card):
# Находим позицию карты card в колонке
        index = self.cards.index(card)
# Удаляем карту card из колонки и помещаем ее во временный список cards
        self.cards, cards = self.cards[:index], self.cards[index:]

# Для всех перемещаемых карт
        for card in cards:
# очищаем привяку к владельцу
            card.setParentItem(None)
# Карта уже не принадлежит никакой колоде или колонке игрового поля - она сложена
            card.stack = None

# Обновляем отображение колонок игрового поля
        self.update()
# Возвращаем перемещаемые карты (в списке 1 карта)
        return cards

# Метод remove_all_cards удаляет все карты в колоде self колонки
    def remove_all_cards(self):
        for card in self.cards[:]:
            card.setParentItem(None)
            card.stack = None
        self.cards = []

# Метод update обновляет отображение карт в колонке
    def update(self):
# Перед обновлением отображения скрываем карты в колонке
        self.stack.setZValue(-1)
        offset_y = 0
# Каждая карта в колонке смещается по вертикали
        for n, card in enumerate(self.cards):
            card.setPos(QPointF(0, offset_y))

            if card.is_face_up:
# Открытая на расстояние self.offset_y
                offset_y = self.offset_y
            else:
# Закрытая на расстояние self.offset_y_back
                offset_y = self.offset_y_back

# Класс DropStack описывает колоды уже сложенных карт
class DropStack(StackBase):

    offset_x = -0.2
    offset_y = -0.3
# Переменные для карты, которую складывают (масть, старшинство)
    suit = None
    value = 0

# Метод setup обновляет отображение карт в колонке
    def setup(self):
# В переменной signals сохраняем ссылку на объект-обработчик сигналов
        self.signals = Signals()
# Задаем визуальное оформление 2D-областей для сложенных колод,
# обводим их жирой голубой рамкой
        color = QColor(Qt.blue)
        color.setAlpha(50)
        pen = QPen(color)
        pen.setWidth(5)
        self.setPen(pen)

# Метод reset обновляет отображение карт в колонке
    def reset(self):
# Вызов метод reset родительского класса StackBase
        super(DropStack, self).reset()
# Инмциализация переменных
        self.suit = None
        self.value = 0

# Метод is_valid_drop определяет, можно ли сложить карту card
# если коолода еще пуста или если масти карты совпадает и складываемая карта
# следующая по старшинству, тогда ДА, иначе НЕТ
    def is_valid_drop(self, card):
        if ((self.suit is None or card.suit == self.suit) and
                (card.value == self.value + 1)):
            return True

        return False

# Метод add_card добавляет карту card в колоду складывания
    def add_card(self, card, update=True):
# Вызов метод add_card родительского класса StackBase
        super(DropStack, self).add_card(card, update=update)
# Запоминаем сложенную карту в переменных
        self.suit = card.suit
        self.value = self.cards[-1].value

# Если колода текущей масти сложена полностью
        if self.is_complete:
# Генерируем событие сигнала complete
            self.signals.complete.emit()

# Метод remove_card удаляет карту card из колоды складывания
    def remove_card(self, card):
# Вызов метод remove_card родительского класса StackBase
        super(DropStack, self).remove_card(card)
# Восстанавливаем старшинство предидущей карты
        self.value = self.cards[-1].value if self.cards else 0

# Свойство is_complete равно TRUE кода старшинство текущей карты равно королю
    @property
    def is_complete(self):
        return self.value == 13


# Вспомогательный класс DealTrigger - это прямоугольная 2D-область размера DEAL_RECT,
# в пределах которой перехватывается событие клика мышкой
class DealTrigger(QGraphicsRectItem):

    def __init__(self, *args, **kwargs):
        super(DealTrigger, self).__init__(*args, **kwargs)
        self.setRect(QRectF(DEAL_RECT))
        self.setZValue(1000)

        pen = QPen(Qt.NoPen)
        self.setPen(pen)

        self.signals = Signals()

# переопределение типового обработчика события клика мышки
    def mousePressEvent(self, e):
# Генерируем свой синал clicked, который вызывает метод deal()
        self.signals.clicked.emit()

# Вспомогательный класс AnimationCover - это прямоугольная 2D-область по размеру главного окна
# в этой области будет графическая анимация
class AnimationCover(QGraphicsRectItem):
    def __init__(self, *args, **kwargs):
        super(AnimationCover, self).__init__(*args, **kwargs)
        self.setRect(QRectF(0, 0, *WINDOW_SIZE))
# Слой области помещаем над всеми остальными слоями
        self.setZValue(5000)
# Убираем рамки
        pen = QPen(Qt.NoPen)
        self.setPen(pen)

# переопределение типового обработчика события клика мышки
    def mousePressEvent(self, e):
        e.accept()

# Класс главного окна унаследован от класса QMainWindow
class MainWindow(QMainWindow):

# Конструктор класс содержит все действия выполняемые при создании главного окна
    def __init__(self, *args, **kwargs):
# Вызываем метод конструктора у объекта-предка
        super(MainWindow, self).__init__(*args, **kwargs)

# Создаем объект view - это базовая графическая поверхность на которой будут жить
# все элементы игровой 2D-графики
# http://doc.crossplatform.ru/qt/4.5.0/qgraphicsview.html
        view = QGraphicsView()
# Создаем объект сцены класса QGraphicsScene, он предоставляет поверхность для управления большим числом графических 2D элементов.
# Размещаем его на поверхности view для отображения графических объектов,
# таких как линии, прямоугольники, текст или даже собственные элементы на двухмерной поверхности. QGraphicsScene водит в каркас графического представления.
# http://doc.crossplatform.ru/qt/4.5.0/qgraphicsscene.html
        self.scene = QGraphicsScene()
# Устанавливаем размер сцены по размеру главного окна
        self.scene.setSceneRect(QRectF(0, 0, *WINDOW_SIZE))

# Создаем объект felt - это объект определяющий параметры закраски фона,
# в качестве фона получает графический объект класса QPixmap, созданный графического файла 'felt.png'
# http://doc.crossplatform.ru/qt/4.5.0/qpixmap.html
# http://doc.crossplatform.ru/qt/4.5.0/qbrush.html
        felt = QBrush(QPixmap(os.path.join("images","felt.png")))
# Устанавливаем фон сцены
        self.scene.setBackgroundBrush(felt)

# Создаем name - это графический оъект стилизованной надписи "Ronery" из
# граф. файла "ronery.png"
# http://doc.crossplatform.ru/qt/4.5.0/qgraphicspixmapitem.html
        name = QGraphicsPixmapItem()
        name.setPixmap(QPixmap(os.path.join("images","ronery.png")))
# Позиционируем надпись и размещаем ее на сцене
        name.setPos(QPointF(170, 375))
        self.scene.addItem(name)

# Устанавливаем сцену
        view.setScene(self.scene)

# Создаем объект таймера, который запускае каждые 5 миллисекунд метод окна win_animation
# реализует анимацию в окне (прыгают карты после окончания игры)
# http://doc.crossplatform.ru/qt/4.5.0/qtimer.html
        self.timer = QTimer()
        self.timer.setInterval(5)
        self.timer.timeout.connect(self.win_animation)

# Создаем вспомогательный для анимации объект и помещаем его на сцену
        self.animation_event_cover = AnimationCover()
        self.scene.addItem(self.animation_event_cover)

# Делаем меню
# Создаем объект меню с именем "Game" и добавляем его в строку меню окна
        menu = self.menuBar().addMenu("&Game")

# Создаем команду меню в виде пункта выбора, оформляем ее иконкой из файла "playing-card.png" и называем ее "Deal..."
# класс QAction описывает объекты абстрактного действия
# http://doc.crossplatform.ru/qt/4.5.0/qaction.html
        deal_action = QAction(QIcon(os.path.join("images", "playing-card.png")), "Deal...", self)
# В качестве обработчика команды назначаем наш метод restart_game
        deal_action.triggered.connect(self.restart_game)
# Добавляем команду в меню "Game"
        menu.addAction(deal_action)

# Добавляем в меню разделитель
        menu.addSeparator()

# Создаем команду меню в виде чекбокса и называем ее "1 card"
        deal1_action = QAction("1 card", self)
        deal1_action.setCheckable(True)
# В качестве обработчика команды назначаем наш метод set_deal_n,
# который устанавливает значение переменной класса deal_n
        deal1_action.triggered.connect(lambda: self.set_deal_n(1))
        menu.addAction(deal1_action)

# Аналогично создаем и добавляем в меню команду "3 card"
        deal3_action = QAction("3 card", self)
        deal3_action.setCheckable(True)
        deal3_action.setChecked(True)
        deal3_action.triggered.connect(lambda: self.set_deal_n(3))

        menu.addAction(deal3_action)

# Объект dealgroup обединяе команды в группу
        dealgroup = QActionGroup(self)
        dealgroup.addAction(deal1_action)
        dealgroup.addAction(deal3_action)
        dealgroup.setExclusive(True)

# Аналогично заполняем меню другими командами"
        menu.addSeparator()

        rounds3_action = QAction("3 rounds", self)
        rounds3_action.setCheckable(True)
        rounds3_action.setChecked(True)
        rounds3_action.triggered.connect(lambda: self.set_rounds_n(3))
        menu.addAction(rounds3_action)

        rounds5_action = QAction("5 rounds", self)
        rounds5_action.setCheckable(True)
        rounds5_action.triggered.connect(lambda: self.set_rounds_n(5))
        menu.addAction(rounds5_action)

        roundsu_action = QAction("Unlimited rounds", self)
        roundsu_action.setCheckable(True)
        roundsu_action.triggered.connect(lambda: self.set_rounds_n(None))
        menu.addAction(roundsu_action)

        roundgroup = QActionGroup(self)
        roundgroup.addAction(rounds3_action)
        roundgroup.addAction(rounds5_action)
        roundgroup.addAction(roundsu_action)
        roundgroup.setExclusive(True)

        menu.addSeparator()

        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.quit)
        menu.addAction(quit_action)

# Инициализируем переменные класса значениями по кмолчанию
        self.deck = []  # Массив - хранящий колоду всех игральных карт
        self.deal_n = 3  # Количество карт каждой сдаче
        self.rounds_n = 3  # Максимальное число раундов (переборов колоды карт) в течении игры

# Заполняем колоду всех карт объектами класса Card (игральная карта)
# Добовляем объекты карт на сцену
        for suit in SUITS:
            for value in range(1, 14):
                card = Card(value, suit)
                self.deck.append(card)
                self.scene.addItem(card)
                card.signals.doubleclicked.connect(lambda card=card: self.auto_drop_card(card))

# Устанавливаем грф. поверхность
        self.setCentralWidget(view)
        self.setFixedSize(*WINDOW_SIZE)

# Устанавливаем массив карт которые остались в колоде из
# которой будет происходить сдача карт игроку - колода сдачи
# тут пока лишь создаем статический класс DeckStack (заполняться будет далее) и сохраняем
# ссылку на его объект в поле deckstack
        self.deckstack = DeckStack()
        self.deckstack.setPos(OFFSET_X, OFFSET_Y)
# Добовляем колоду сдачи на сцену
        self.scene.addItem(self.deckstack)

# Поле works - это массив в котором храняться 7 колонок с картами,
# в которых игрок ведет их перекладку
# Инициализируем 7 игровых колонок (стеков)
# 1-я колонка будет содержать 1 карту, 2-я две и т.д.
        self.works = []
        for n in range(7):
# Создаем игровую колонку (стеко)
            stack = WorkStack()
            stack.setPos(OFFSET_X + CARD_SPACING_X*n, WORK_STACK_Y)
# Добовляем игровую колонку на сцену
            self.scene.addItem(stack)
            self.works.append(stack)

# Поле drops - это массив в котором храняться карты уже сложенные
# в 4 колоды по мастям - колоды складывания
# так же пока лишь создаем статический класс DropStack (заполняться будет далее) и сохраняем
# ссылку на его объект в поле drops
        self.drops = []
        for n in range(4):
            stack = DropStack()
            stack.setPos(OFFSET_X + CARD_SPACING_X * (3+n), OFFSET_Y)
# к каждой колоде складывания будем прицеплять обработчик событий check_win_condition
# который будет проверять их состояние (если все 4 колоды складывания заполнены тогда GAME OVER)
            stack.signals.complete.connect(self.check_win_condition)

# Добовляем колоду складывания на сцену
            self.scene.addItem(stack)
            self.drops.append(stack)

# Поле dealstack - это массив в котором храняться уже сданные игроку карты
# так же пока лишь создаем статический класс DealStack (заполняться будет далее) и сохраняем
        self.dealstack = DealStack()
        self.dealstack.setPos(OFFSET_X + CARD_SPACING_X, OFFSET_Y)
        self.scene.addItem(self.dealstack)

# Создаем вспомогательную переменную dealtrigger через которую мы подключим обработчик
# клика мышкой для сдачи карт в массив dealstack
        dealtrigger = DealTrigger()
        dealtrigger.signals.clicked.connect(self.deal)
# Добавляем объект dealtrigger на сцену, но он не виден
        self.scene.addItem(dealtrigger)

# Выполняем заполнение в случайном порядке всех игровых массивов картами
        self.shuffle_and_stack()

# Устанавливаем заголовок в главном окне и показываем его
        self.setWindowTitle("Ronery")
        self.show()
# Конец создания главного окна

# Метод restart_game перезапускает игру
    def restart_game(self):
# Спрашиваем игрока
        reply = QMessageBox.question(self, "Deal again", "Are you sure you want to start a new game?",
                                     QMessageBox.Yes | QMessageBox.No)

        if reply == QMessageBox.Yes:
            self.shuffle_and_stack()

# Выход из игры
    def quit(self):
# Закрываем главное окно
        self.close()

# Сеттер количеств карт в сдаче
    def set_deal_n(self, n):
        self.deal_n = n

# Сеттер количеств раундов сдачи
    def set_rounds_n(self, n):
        self.rounds_n = n
        self.deckstack.update_stack_status(self.rounds_n)

# Данная процедура объединяет все действия выполняемые при начальном запуске (перезапуске) игры
    def shuffle_and_stack(self):
# в случае если это перезапуск игры, тогда завершение предидущей игры включило аниммирование движение карт,
# поэтому тут останавливаем таймер анимации и скрываем на сцене 2D-слой анимации animation_event_cover
        self.timer.stop()
        self.animation_event_cover.hide()

# У всех колод (для сдачи, открытые сдачи, 4 сложенные, 7 игровых) вызываем метод перезаполнения картами вслучайном порядке
        for stack in [self.deckstack, self.dealstack] + self.drops + self.works:
            stack.reset()

# Поле deck - массив (колода) всех игральх карт, котораая заново перемешивается (тусуется) методом random.shuffle
        random.shuffle(self.deck)

# Во временную переменную- список cards копируем все карты из колоды
        cards = self.deck[:]
        for n, workstack in enumerate(self.works, 1):
# переменная n принимает значение от 1 до 7 (размерность массива works)
# переменная workstack будет хранить массив карт для каждой игровой колонки
# https://all-python.ru/osnovy/enumerate.html
            for a in range(n):
# Забираем из списка теущую карту и сохраняем ее в переменной card
                card = cards.pop()
# Помещаем эту карту в колоду текущей n-ой колонки
                workstack.add_card(card)
# Метод turn_back_up объекта Card переключает ее визуальное отображение на рубашку
                card.turn_back_up()
# Если номер карты текущей колоде = максимальному резмеру этой колоды,
# тогда эту карту показываем открытой
                if a == n-1:
                    card.turn_face_up()

# Оставшиеся в списке cards карты, метод stack_cards перемещает в колоду для сдачи
        self.deckstack.stack_cards(cards)

# Метод deal - сдача карт, вызывается по сигналу клика мышкой в 2D-области колоды
    def deal(self):
        if self.deckstack.cards:
# Если колода еще не пуста, то запоминаем в поле spread_from количество уже сданных карт
            self.dealstack.spread_from = len(self.dealstack.cards)
            for n in range(self.deal_n):
# Каждую их сдаваем карт, перемещаем из колоды в переменную card
                card = self.deckstack.take_top_card()
                if card:
# Помещаем в колоду сдачи
                    self.dealstack.add_card(card)
# Открываем карту лицом к верху
                    card.turn_face_up()

        elif self.deckstack.can_restack(self.rounds_n):
# Если колода пуста, тогда проверяем доступен ли еще раунд раздачи и если да то,
# вновь заполняем колоду сданными картами
            self.deckstack.restack(self.dealstack)
# Обновляем графическое отображение колод
            self.deckstack.update_stack_status(self.rounds_n)

# Метод auto_drop_card - помещение карты в колоду укладки,
# вызывается по сигналу двойного клика мышкой в 2D-области карты
    def auto_drop_card(self, card):
        for stack in self.drops:
# Для каждой из 4-х колод укладки dызываем проверку можно помещать данную карту в колоду
            if stack.is_valid_drop(card):
# Если да, то удаляем ее из текущей колоду
                card.stack.remove_card(card)
# Добавляем ее в колоду укладки
                stack.add_card(card)
                break

# Метод check_win_condition проверяет завершена ли игра
    def check_win_condition(self):
# Если все 4 колоды укладки dызываем полностью заполнены
        complete = all(s.is_complete for s in self.drops)
        if complete:
# то ДА и тогда запускаем анимацию
            self.animation_event_cover.show()
            self.timer.start()

# Метод win_animation запускает анимацию
    def win_animation(self):
        for drop in self.drops:
            if drop.cards:
                card = drop.cards.pop()
                if card.vector is None:
                    card.vector = QPoint(-random.randint(3, 10), -random.randint(0, 10))
                    break

        for card in self.deck:
            if card.vector is not None:
                card.setPos(card.pos() + card.vector)
                card.vector += QPoint(0, 1)
                if card.pos().y() > WINDOW_SIZE[1] - CARD_DIMENSIONS.height():
                    card.vector = QPoint(card.vector.x(), -max(1, int(card.vector.y() * BOUNCE_ENERGY)))
                    card.setPos(card.pos().x(), WINDOW_SIZE[1] - CARD_DIMENSIONS.height())

                if card.pos().x() < - CARD_DIMENSIONS.width():
                    card.vector = None
                    card.stack.add_card(card)




if __name__ == '__main__':
# Создаем глобальный объект игры
    app = QApplication([])
# Создаем объект игрового окна
    window = MainWindow()
    app.exec_()