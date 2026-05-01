import math
import re
from dataclasses import dataclass
from typing import List, Optional
from collections import defaultdict


@dataclass
class Issue:
    line_no: int
    severity: str  # ERROR, WARNING, INFO
    message: str
    line: str


# --- DİL SÖZLÜĞÜ (GCode Checker İçin Tam Liste) ---
DICT_GC = {
    "TR": {
        "read_err": "Dosya okunamadı. Encoding bozuk olabilir.",
        "short_file": "Dosya çok kısa görünüyor. Eksik veya yarım yazılmış olabilir.",
        "null_byte": "Satırda bozuk karakter veya null byte bulundu.",
        "bad_format": "Satır komut formatına benzemiyor.",
        "x_out": "X koordinatı tabla sınırları dışında görünüyor",
        "y_out": "Y koordinatı tabla sınırları dışında görünüyor",
        "z_out": "Z yüksekliği sınır dışında görünüyor",
        "jump_x": "X ekseninde büyük sıçrama var",
        "jump_y": "Y ekseninde büyük sıçrama var",
        "jump_z": "Z ekseninde büyük sıçrama var",
        "f_zero": "Feedrate sıfır veya negatif",
        "f_high": "Feedrate çok yüksek görünüyor",
        "e_jump": "Extrusion değerinde anormal büyük değişim",
        "early_end": "Program sonu komutu çok erken bulundu.",
        "no_move": "Dosyada hareket komutu (G0/G1/G2/G3) bulunamadı.",
        "no_layer": "Slicer layer (katman) bilgisi eklememiş.",
        # Yapısal Analiz Mesajları
        "str_g21_ok": "Milimetre birimi (G21) bulundu.",
        "str_g21_warn": "G21 bulunamadı. Firmware varsayılanına kalır.",
        "str_g28_ok": "Home (G28) komutu bulundu.",
        "str_g28_err": "G28 bulunamadı! Yazıcı konumunu bilmeden başlayabilir.",
        "str_noz_ok": "Nozzle ısıtma komutu bulundu.",
        "str_noz_err": "Nozzle ısıtma komutu (M104/M109) bulunamadı.",
        "str_noz_wait_ok": "Nozzle ısınma beklemesi (M109) var.",
        "str_noz_wait_warn": "M109 yok. Yazıcı ısınmadan harekete geçebilir.",
        "str_bed_ok": "Tabla ısıtma komutu bulundu.",
        "str_bed_warn": "Tabla ısıtma komutu bulunamadı.",
        "str_bed_wait_ok": "Tabla ısınma beklemesi (M190) var.",
        "str_bed_wait_info": "M190 yok. Dosya veya materyal için gerekmeyebilir.",
        "str_ext_warn": "M82/M83 bulunamadı. Extrusion modu belirsiz.",
        "str_first_err": "Geçerli bir hareket komutu yok.",
        "str_noff_ok": "Baskı sonu Nozzle kapatma (M104 S0) var.",
        "str_noff_warn": "Baskı sonunda Nozzle açık kalabilir!",
        "str_boff_ok": "Baskı sonu Tabla kapatma (M140 S0) var.",
        "str_boff_warn": "Baskı sonunda Tabla sıcak kalabilir!",
        "str_fan_ok": "Baskı sonu Fan kapatma (M107) var.",
        "str_fan_info": "Fan kapatma komutu bulunamadı.",
        "str_mot_ok": "Motor kapatma (M84/M18) var.",
        "str_mot_info": "Motor kapatma komutu bulunamadı.",
        "str_klip_start": "Klipper başlangıç makrosu bulundu. Isıtma/Home makro içinde varsayıldı.",
        "str_klip_end": "Klipper bitiş makrosu bulundu. Kapatma işlemleri makro içinde varsayıldı."
    },
    "EN": {
        "read_err": "Could not read file. Encoding issue.",
        "short_file": "File seems too short. Might be incomplete.",
        "null_byte": "Null byte or corrupted character found.",
        "bad_format": "Line does not match a command format.",
        "x_out": "X coordinate out of bed bounds",
        "y_out": "Y coordinate out of bed bounds",
        "z_out": "Z height out of bounds",
        "jump_x": "Large jump on X axis",
        "jump_y": "Large jump on Y axis",
        "jump_z": "Large jump on Z axis",
        "f_zero": "Feedrate is zero or negative",
        "f_high": "Feedrate seems too high",
        "e_jump": "Abnormal change in extrusion",
        "early_end": "End of program command found too early.",
        "no_move": "No G0/G1/G2/G3 movement commands found.",
        "no_layer": "No layer comments found.",
        "str_g21_ok": "Units set to mm (G21).",
        "str_g21_warn": "G21 missing. Relying on firmware default.",
        "str_g28_ok": "Homing (G28) found.",
        "str_g28_err": "G28 missing! Printer might crash.",
        "str_noz_ok": "Nozzle heat command found.",
        "str_noz_err": "Nozzle heat command missing.",
        "str_noz_wait_ok": "Wait for nozzle temp (M109) found.",
        "str_noz_wait_warn": "M109 missing. Printer might move while cold.",
        "str_bed_ok": "Bed heat command found.",
        "str_bed_warn": "Bed heat command missing.",
        "str_bed_wait_ok": "Wait for bed temp (M190) found.",
        "str_bed_wait_info": "M190 missing.",
        "str_ext_warn": "M82/M83 missing. Extrusion mode uncertain.",
        "str_first_err": "No valid movement command.",
        "str_noff_ok": "Nozzle turned off at the end.",
        "str_noff_warn": "Nozzle might stay hot at the end!",
        "str_boff_ok": "Bed turned off at the end.",
        "str_boff_warn": "Bed might stay hot at the end!",
        "str_fan_ok": "Fan turned off at the end.",
        "str_fan_info": "No fan off command found.",
        "str_mot_ok": "Motors disabled at the end.",
        "str_mot_info": "No motor disable command found.",
        "str_klip_start": "Klipper start macro found. Homing and heating assumed to be handled inside.",
        "str_klip_end": "Klipper end macro found. Shutdowns assumed to be handled inside."
    },
    "ES": {
        "read_err": "No se pudo leer el archivo. Problema de codificación.",
        "short_file": "El archivo parece demasiado corto.",
        "null_byte": "Byte nulo o carácter corrupto encontrado.",
        "bad_format": "La línea no coincide con el formato de comando.",
        "x_out": "Coordenada X fuera de los límites",
        "y_out": "Coordenada Y fuera de los límites",
        "z_out": "Altura Z fuera de los límites",
        "jump_x": "Gran salto en el eje X",
        "jump_y": "Gran salto en el eje Y",
        "jump_z": "Gran salto en el eje Z",
        "f_zero": "Feedrate es cero o negativo",
        "f_high": "Feedrate parece demasiado alto",
        "e_jump": "Cambio anormal en extrusión",
        "early_end": "Comando de fin de programa demasiado pronto.",
        "no_move": "No se encontraron comandos de movimiento.",
        "no_layer": "No se encontraron comentarios de capa.",
        "str_g21_ok": "Unidades configuradas a mm (G21).",
        "str_g21_warn": "G21 ausente. Se usará el valor por defecto.",
        "str_g28_ok": "Homing (G28) encontrado.",
        "str_g28_err": "¡G28 ausente! La impresora podría chocar.",
        "str_noz_ok": "Comando de calentamiento de boquilla encontrado.",
        "str_noz_err": "Comando de calentamiento de boquilla ausente.",
        "str_noz_wait_ok": "Espera de temperatura (M109) encontrada.",
        "str_noz_wait_warn": "M109 ausente. Podría moverse en frío.",
        "str_bed_ok": "Comando de calentamiento de cama encontrado.",
        "str_bed_warn": "Comando de calentamiento de cama ausente.",
        "str_bed_wait_ok": "Espera de temperatura de cama (M190) encontrada.",
        "str_bed_wait_info": "M190 ausente.",
        "str_ext_warn": "M82/M83 ausente. Modo de extrusión incierto.",
        "str_first_err": "Ningún comando de movimiento válido.",
        "str_noff_ok": "Boquilla apagada al final.",
        "str_noff_warn": "¡La boquilla podría quedarse caliente!",
        "str_boff_ok": "Cama apagada al final.",
        "str_boff_warn": "¡La cama podría quedarse caliente!",
        "str_fan_ok": "Ventilador apagado al final.",
        "str_fan_info": "Comando apagar ventilador ausente.",
        "str_mot_ok": "Motores desactivados al final.",
        "str_mot_info": "Comando desactivar motores ausente.",
        "str_klip_start": "Macro de inicio de Klipper encontrada.",
        "str_klip_end": "Macro de fin de Klipper encontrada."
    },
    "DE": {
        "read_err": "Datei konnte nicht gelesen werden.",
        "short_file": "Datei scheint zu kurz zu sein.",
        "null_byte": "Nullbyte oder beschädigtes Zeichen gefunden.",
        "bad_format": "Zeile entspricht keinem Befehlsformat.",
        "x_out": "X-Koordinate außerhalb der Bettgrenzen",
        "y_out": "Y-Koordinate außerhalb der Bettgrenzen",
        "z_out": "Z-Höhe außerhalb der Grenzen",
        "jump_x": "Großer Sprung auf der X-Achse",
        "jump_y": "Großer Sprung auf der Y-Achse",
        "jump_z": "Großer Sprung auf der Z-Achse",
        "f_zero": "Vorschub ist null oder negativ",
        "f_high": "Vorschub scheint zu hoch zu sein",
        "e_jump": "Abnormale Änderung der Extrusion",
        "early_end": "Programmende-Befehl zu früh gefunden.",
        "no_move": "Keine Bewegungsbefehle gefunden.",
        "no_layer": "Keine Schichtkommentare gefunden.",
        "str_g21_ok": "Einheiten auf mm (G21) gesetzt.",
        "str_g21_warn": "G21 fehlt. Firmware-Standard wird verwendet.",
        "str_g28_ok": "Homing (G28) gefunden.",
        "str_g28_err": "G28 fehlt! Drucker könnte crashen.",
        "str_noz_ok": "Düsenheizbefehl gefunden.",
        "str_noz_err": "Düsenheizbefehl fehlt.",
        "str_noz_wait_ok": "Warten auf Düsentemperatur (M109) gefunden.",
        "str_noz_wait_warn": "M109 fehlt. Drucker könnte sich kalt bewegen.",
        "str_bed_ok": "Bett-Heizbefehl gefunden.",
        "str_bed_warn": "Bett-Heizbefehl fehlt.",
        "str_bed_wait_ok": "Warten auf Bett-Temperatur (M190) gefunden.",
        "str_bed_wait_info": "M190 fehlt.",
        "str_ext_warn": "M82/M83 fehlt. Extrusionsmodus unsicher.",
        "str_first_err": "Kein gültiger Bewegungsbefehl.",
        "str_noff_ok": "Düse am Ende ausgeschaltet.",
        "str_noff_warn": "Düse könnte am Ende heiß bleiben!",
        "str_boff_ok": "Bett am Ende ausgeschaltet.",
        "str_boff_warn": "Bett könnte am Ende heiß bleiben!",
        "str_fan_ok": "Lüfter am Ende ausgeschaltet.",
        "str_fan_info": "Kein Befehl zum Ausschalten des Lüfters gefunden.",
        "str_mot_ok": "Motoren am Ende deaktiviert.",
        "str_mot_info": "Kein Befehl zur Deaktivierung der Motoren gefunden.",
        "str_klip_start": "Klipper Start-Makro gefunden.",
        "str_klip_end": "Klipper End-Makro gefunden."
    },
    "FR": {
        "read_err": "Impossible de lire le fichier.",
        "short_file": "Le fichier semble trop court.",
        "null_byte": "Octet nul ou caractère corrompu trouvé.",
        "bad_format": "La ligne ne correspond pas à un format de commande.",
        "x_out": "Coordonnée X hors limites",
        "y_out": "Coordonnée Y hors limites",
        "z_out": "Hauteur Z hors limites",
        "jump_x": "Grand saut sur l'axe X",
        "jump_y": "Grand saut sur l'axe Y",
        "jump_z": "Grand saut sur l'axe Z",
        "f_zero": "Le Feedrate est nul ou négatif",
        "f_high": "Le Feedrate semble trop élevé",
        "e_jump": "Changement anormal de l'extrusion",
        "early_end": "Commande de fin de programme trouvée trop tôt.",
        "no_move": "Aucune commande de mouvement trouvée.",
        "no_layer": "Aucun commentaire de couche trouvé.",
        "str_g21_ok": "Unités réglées sur mm (G21).",
        "str_g21_warn": "G21 manquant. Utilisation du défaut du firmware.",
        "str_g28_ok": "Homing (G28) trouvé.",
        "str_g28_err": "G28 manquant ! L'imprimante pourrait planter.",
        "str_noz_ok": "Commande de chauffe de la buse trouvée.",
        "str_noz_err": "Commande de chauffe de la buse manquante.",
        "str_noz_wait_ok": "Attente de la température de la buse (M109) trouvée.",
        "str_noz_wait_warn": "M109 manquant. L'imprimante pourrait bouger à froid.",
        "str_bed_ok": "Commande de chauffe du plateau trouvée.",
        "str_bed_warn": "Commande de chauffe du plateau manquante.",
        "str_bed_wait_ok": "Attente de la température du plateau (M190) trouvée.",
        "str_bed_wait_info": "M190 manquant.",
        "str_ext_warn": "M82/M83 manquant. Mode d'extrusion incertain.",
        "str_first_err": "Aucune commande de mouvement valide.",
        "str_noff_ok": "Buse éteinte à la fin.",
        "str_noff_warn": "La buse pourrait rester chaude à la fin !",
        "str_boff_ok": "Plateau éteint à la fin.",
        "str_boff_warn": "Le plateau pourrait rester chaud à la fin !",
        "str_fan_ok": "Ventilateur éteint à la fin.",
        "str_fan_info": "Aucune commande pour éteindre le ventilateur.",
        "str_mot_ok": "Moteurs désactivés à la fin.",
        "str_mot_info": "Aucune commande pour désactiver les moteurs.",
        "str_klip_start": "Macro de démarrage Klipper trouvée.",
        "str_klip_end": "Macro de fin Klipper trouvée."
    },
    "ZH": {
        "read_err": "无法读取文件。编码问题。",
        "short_file": "文件似乎太短。可能不完整。",
        "null_byte": "发现空字节或损坏的字符。",
        "bad_format": "该行与命令格式不匹配。",
        "x_out": "X 坐标超出边界",
        "y_out": "Y 坐标超出边界",
        "z_out": "Z 高度超出边界",
        "jump_x": "X 轴大跳跃",
        "jump_y": "Y 轴大跳跃",
        "jump_z": "Z 轴大跳跃",
        "f_zero": "进给率为零或负数",
        "f_high": "进给率似乎太高",
        "e_jump": "挤出异常变化",
        "early_end": "过早发现程序结束命令。",
        "no_move": "未找到移动命令。",
        "no_layer": "未找到层注释。",
        "str_g21_ok": "单位设置为毫米 (G21)。",
        "str_g21_warn": "缺少 G21。依赖固件默认值。",
        "str_g28_ok": "找到归位 (G28)。",
        "str_g28_err": "缺少 G28！打印机可能会碰撞。",
        "str_noz_ok": "找到喷嘴加热命令。",
        "str_noz_err": "缺少喷嘴加热命令。",
        "str_noz_wait_ok": "找到等待喷嘴温度 (M109)。",
        "str_noz_wait_warn": "缺少 M109。打印机可能在冷态下移动。",
        "str_bed_ok": "找到热床加热命令。",
        "str_bed_warn": "缺少热床加热命令。",
        "str_bed_wait_ok": "找到等待热床温度 (M190)。",
        "str_bed_wait_info": "缺少 M190。",
        "str_ext_warn": "缺少 M82/M83。挤出模式不确定。",
        "str_first_err": "没有有效的移动命令。",
        "str_noff_ok": "喷嘴在结束时已关闭。",
        "str_noff_warn": "喷嘴在结束时可能会保持高温！",
        "str_boff_ok": "热床在结束时已关闭。",
        "str_boff_warn": "热床在结束时可能会保持高温！",
        "str_fan_ok": "风扇在结束时已关闭。",
        "str_fan_info": "未找到关闭风扇命令。",
        "str_mot_ok": "电机在结束时已禁用。",
        "str_mot_info": "未找到禁用电机命令。",
        "str_klip_start": "找到 Klipper 启动宏。",
        "str_klip_end": "找到 Klipper 结束宏。"
    },
    "RU": {
        "read_err": "Не удалось прочитать файл. Проблема с кодировкой.",
        "short_file": "Файл кажется слишком коротким.",
        "null_byte": "Найден нулевой байт или поврежденный символ.",
        "bad_format": "Строка не соответствует формату команды.",
        "x_out": "Координата X выходит за границы",
        "y_out": "Координата Y выходит за границы",
        "z_out": "Высота Z выходит за границы",
        "jump_x": "Большой скачок по оси X",
        "jump_y": "Большой скачок по оси Y",
        "jump_z": "Большой скачок по оси Z",
        "f_zero": "Подача равна нулю или отрицательна",
        "f_high": "Подача кажется слишком высокой",
        "e_jump": "Аномальное изменение экструзии",
        "early_end": "Команда завершения найдена слишком рано.",
        "no_move": "Не найдены команды движения.",
        "no_layer": "Не найдены комментарии слоев.",
        "str_g21_ok": "Единицы измерения установлены в мм (G21).",
        "str_g21_warn": "G21 отсутствует. Используются настройки по умолчанию.",
        "str_g28_ok": "Команда возврата домой (G28) найдена.",
        "str_g28_err": "G28 отсутствует! Принтер может разбиться.",
        "str_noz_ok": "Команда нагрева сопла найдена.",
        "str_noz_err": "Команда нагрева сопла отсутствует.",
        "str_noz_wait_ok": "Ожидание температуры сопла (M109) найдено.",
        "str_noz_wait_warn": "M109 отсутствует. Принтер может начать движение холодным.",
        "str_bed_ok": "Команда нагрева стола найдена.",
        "str_bed_warn": "Команда нагрева стола отсутствует.",
        "str_bed_wait_ok": "Ожидание температуры стола (M190) найдено.",
        "str_bed_wait_info": "M190 отсутствует.",
        "str_ext_warn": "M82/M83 отсутствует. Режим экструзии неясен.",
        "str_first_err": "Нет действительной команды движения.",
        "str_noff_ok": "Сопло выключено в конце.",
        "str_noff_warn": "Сопло может остаться горячим!",
        "str_boff_ok": "Стол выключен в конце.",
        "str_boff_warn": "Стол может остаться горячим!",
        "str_fan_ok": "Вентилятор выключен в конце.",
        "str_fan_info": "Не найдена команда выключения вентилятора.",
        "str_mot_ok": "Моторы отключены в конце.",
        "str_mot_info": "Не найдена команда отключения моторов.",
        "str_klip_start": "Найден макрос запуска Klipper.",
        "str_klip_end": "Найден макрос завершения Klipper."
    },
    "JA": {
        "read_err": "ファイルを読み込めませんでした。エンコーディングの問題。",
        "short_file": "ファイルが短すぎます。",
        "null_byte": "ヌルバイトまたは破損した文字が検出されました。",
        "bad_format": "コマンドフォーマットに一致しません。",
        "x_out": "X座標が境界外です",
        "y_out": "Y座標が境界外です",
        "z_out": "Zの高さが境界外です",
        "jump_x": "X軸での大きなスキップ",
        "jump_y": "Y軸での大きなスキップ",
        "jump_z": "Z軸での大きなスキップ",
        "f_zero": "送り速度がゼロまたは負です",
        "f_high": "送り速度が高すぎます",
        "e_jump": "押し出しの異常な変化",
        "early_end": "プログラム終了コマンドが早すぎます。",
        "no_move": "移動コマンドが見つかりません。",
        "no_layer": "レイヤーコメントが見つかりません。",
        "str_g21_ok": "単位がmmに設定されています (G21)。",
        "str_g21_warn": "G21がありません。デフォルトに依存します。",
        "str_g28_ok": "ホーミング (G28) が見つかりました。",
        "str_g28_err": "G28がありません！プリンターがクラッシュする可能性があります。",
        "str_noz_ok": "ノズル加熱コマンドが見つかりました。",
        "str_noz_err": "ノズル加熱コマンドがありません。",
        "str_noz_wait_ok": "ノズル温度の待機 (M109) が見つかりました。",
        "str_noz_wait_warn": "M109がありません。プリンターが冷たいまま動く可能性があります。",
        "str_bed_ok": "ベッド加熱コマンドが見つかりました。",
        "str_bed_warn": "ベッド加熱コマンドがありません。",
        "str_bed_wait_ok": "ベッド温度の待機 (M190) が見つかりました。",
        "str_bed_wait_info": "M190がありません。",
        "str_ext_warn": "M82/M83がありません。押し出しモードが不明確です。",
        "str_first_err": "有効な移動コマンドがありません。",
        "str_noff_ok": "終了時にノズルがオフになっています。",
        "str_noff_warn": "終了時にノズルが熱いままになる可能性があります！",
        "str_boff_ok": "終了時にベッドがオフになっています。",
        "str_boff_warn": "終了時にベッドが熱いままになる可能性があります！",
        "str_fan_ok": "終了時にファンがオフになっています。",
        "str_fan_info": "ファンをオフにするコマンドが見つかりません。",
        "str_mot_ok": "終了時にモーターが無効になっています。",
        "str_mot_info": "モーターを無効にするコマンドが見つかりません。",
        "str_klip_start": "Klipper開始マクロが見つかりました。",
        "str_klip_end": "Klipper終了マクロが見つかりました。"
    }
}


class GCodeChecker:
    def __init__(self, bed_x=220, bed_y=220, max_z=250, tolerance=10, lang="TR"):
        self.bed_x = bed_x
        self.bed_y = bed_y
        self.max_z = max_z
        self.tolerance = tolerance
        self.lang = lang

        # Regex: Harf ve sayılar arasındaki boşlukları tolere etmek için tasarlandı (örn: X 10 veya X10)
        self.param_pattern = re.compile(r"([A-Z])\s*([-+]?\d*\.?\d+)")
        
        # Performans artışı: Dosya sadece bir kere okunur ve RAM'de tutulur
        self._path_cache = None
        self._lines_cache = None

    def tr(self, key: str) -> str:
        """Dil sözlüğünden metni getirir. Desteklenmeyen diller için EN döner."""
        return DICT_GC.get(self.lang, DICT_GC["EN"]).get(key, key)

    def read_file(self, path: str) -> List[str]:
        # Eğer aynı dosya daha önce okunduysa, önbellekteki veriyi dön (Performans için kritik)
        if self._path_cache == path and self._lines_cache is not None:
            return self._lines_cache

        encodings = ["utf-8", "latin-1"]

        for enc in encodings:
            try:
                with open(path, "r", encoding=enc) as f:
                    lines = f.readlines()
                    self._path_cache = path
                    self._lines_cache = lines
                    return lines
            except UnicodeDecodeError:
                continue

        raise ValueError(self.tr("read_err"))

    def parse_params(self, code_part: str):
        params = {}
        for key, value in self.param_pattern.findall(code_part):
            try:
                params[key] = float(value)
            except ValueError:
                continue
        return params

    def format_duration(self, seconds: float) -> str:
        if seconds <= 0:
            return "-"

        total_seconds = int(round(seconds))
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        secs = total_seconds % 60

        # Saat birimlerini dile göre ayarlıyoruz
        if self.lang == "TR": h, m, s = "sa", "dk", "sn"
        elif self.lang in ["EN", "ES", "FR"]: h, m, s = "h", "m", "s"
        elif self.lang == "DE": h, m, s = "Std", "Min", "Sek"
        elif self.lang == "ZH": h, m, s = "小时", "分钟", "秒"
        elif self.lang == "RU": h, m, s = "ч", "м", "с"
        elif self.lang == "JA": h, m, s = "時間", "分", "秒"
        else: h, m, s = "h", "m", "s"

        if hours > 0:
            return f"{hours}{h} {minutes}{m} {secs}{s}"
        if minutes > 0:
            return f"{minutes}{m} {secs}{s}"
        return f"{secs}{s}"

    def get_toolpath_points(self, path: str, max_points: int = 50000):
        lines = self.read_file(path)
        points = []

        current_x: Optional[float] = None
        current_y: Optional[float] = None
        current_z: Optional[float] = None
        current_e: Optional[float] = None

        absolute_positioning = True
        relative_extrusion = False

        for raw_line in lines:
            line = raw_line.strip()
            code_part = line.split(";")[0].strip()

            if not code_part:
                continue

            parts = code_part.split()
            command = parts[0].upper()
            params = self.parse_params(code_part)

            if command == "G90":
                absolute_positioning = True
                continue
            if command == "G91":
                absolute_positioning = False
                continue
            if command == "M82":
                relative_extrusion = False
                continue
            if command == "M83":
                relative_extrusion = True
                continue

            # Klipper G2/G3 yay komutları da hareket sayılır
            if command not in {"G0", "G1", "G2", "G3"}:
                continue

            old_x = current_x
            old_y = current_y
            old_z = current_z
            old_e = current_e

            # X, Y ve Z Pozisyonlarının Hesaplanması
            if absolute_positioning:
                new_x = params.get("X", current_x)
                new_y = params.get("Y", current_y)
                new_z = params.get("Z", current_z)
            else:
                new_x = (current_x or 0.0) + params.get("X", 0.0)
                new_y = (current_y or 0.0) + params.get("Y", 0.0)
                new_z = (current_z or 0.0) + params.get("Z", 0.0)

            # Extrusion Değerlerinin Hesaplanması
            if relative_extrusion:
                e_delta = params.get("E", 0.0)
                new_e = (current_e or 0.0) + e_delta
            else:
                new_e = params.get("E", current_e)
                if current_e is None or new_e is None:
                    e_delta = 0.0
                else:
                    e_delta = new_e - current_e

            # Eğer bir hareket olmuşsa bu noktayı kaydet
            if (
                old_x is not None
                and old_y is not None
                and new_x is not None
                and new_y is not None
                and (old_x != new_x or old_y != new_y)
            ):
                move_type = "extrusion" if e_delta > 0 else "travel"

                points.append({
                    "x1": old_x,
                    "y1": old_y,
                    "x2": new_x,
                    "y2": new_y,
                    "z": new_z if new_z is not None else old_z,
                    "type": move_type,
                })

            current_x = new_x
            current_y = new_y
            current_z = new_z
            current_e = new_e

        # Nokta sayısı çok fazlaysa performansı korumak için seyreltme (decimation) uygula
        if len(points) > max_points:
            step = max(1, len(points) // max_points)
            points = points[::step]

        return points

    def analyze_summary(
        self,
        path: str,
        filament_diameter: float = 1.75,
        filament_density: float = 1.24,
    ):
        lines = self.read_file(path)

        # Kapsamlı G-Code İstatistikleri ve Matematiksel Hesaplamalar İçin Durum Sözlüğü
        stats = {
            "total_lines": len(lines),
            "movement_count": 0,
            "layer_count": 0,
            "comment_layer_count": 0,
            "dist_x": 0.0,
            "dist_y": 0.0,
            "dist_z": 0.0,
            "dist_e_raw": 0.0,
            "print_time_sec": 0.0,
            "travel_time_sec": 0.0,
            "print_dist_mm": 0.0,
            "travel_dist_mm": 0.0,
            "retract_count": 0,
            "retract_dist_mm": 0.0,
            "zhop_count": 0,
            "zhop_time_sec": 0.0,
            "f_values": [],
            "nozzle_temps": set(),
            "bed_temps": set(),
            "speed_hist": defaultdict(float) # Hız-Zaman Histogramı Verileri
        }

        current_x: Optional[float] = None
        current_y: Optional[float] = None
        current_z: Optional[float] = None
        current_e: Optional[float] = None
        current_f: Optional[float] = None

        absolute_positioning = True
        relative_extrusion = False
        z_layer_values = set()

        for raw_line in lines:
            line_str = raw_line.strip()

            if line_str.startswith(";LAYER:"):
                stats["comment_layer_count"] += 1
                stats["layer_count"] += 1

            code_part = line_str.split(";")[0].strip()
            if not code_part:
                continue

            parts = code_part.split()
            command = parts[0].upper()
            params = self.parse_params(code_part)

            if command == "G90":
                absolute_positioning = True
            elif command == "G91":
                absolute_positioning = False
            elif command == "M82":
                relative_extrusion = False
            elif command == "M83":
                relative_extrusion = True
            elif command in {"M104", "M109"} and "S" in params:
                stats["nozzle_temps"].add(params["S"])
            elif command in {"M140", "M190"} and "S" in params:
                stats["bed_temps"].add(params["S"])
            # Firmware Retraction (Klipper G10/G11) Tespiti
            elif command == "G10":
                stats["retract_count"] += 1
            elif command == "G11":
                pass # Unretract işlemi, mesafesini tam bilemediğimiz için sadece algılayıp geçiyoruz

            # Tüm hareket komutları (Arc dahil)
            if command not in {"G0", "G1", "G2", "G3"}:
                continue

            stats["movement_count"] += 1

            old_x = current_x
            old_y = current_y
            old_z = current_z

            if "F" in params:
                current_f = params["F"]
                stats["f_values"].append(current_f)

            if absolute_positioning:
                new_x = params.get("X", current_x)
                new_y = params.get("Y", current_y)
                new_z = params.get("Z", current_z)
            else:
                new_x = (current_x or 0.0) + params.get("X", 0.0)
                new_y = (current_y or 0.0) + params.get("Y", 0.0)
                new_z = (current_z or 0.0) + params.get("Z", 0.0)

            if relative_extrusion:
                e_delta = params.get("E", 0.0)
            else:
                new_e = params.get("E", current_e)
                e_delta = 0.0 if current_e is None or new_e is None else new_e - current_e

            dx = 0.0 if old_x is None or new_x is None else new_x - old_x
            dy = 0.0 if old_y is None or new_y is None else new_y - old_y
            dz = 0.0 if old_z is None or new_z is None else new_z - old_z

            if new_z is not None:
                z_layer_values.add(round(new_z, 4))

            # 3D Uzaydaki Hareket Mesafesi
            dist = math.sqrt(dx * dx + dy * dy + dz * dz)
            
            stats["dist_x"] += abs(dx)
            stats["dist_y"] += abs(dy)
            stats["dist_z"] += abs(dz)

            # Zaman ve Histogram Hesaplaması
            move_time = 0.0
            if current_f and current_f > 0 and dist > 0:
                move_time = (dist / current_f) * 60 # Süre = (Mesafe / Hız) * 60
                bin_speed = round(current_f, -2)    # Yüzlük dilimlere yuvarlama (örn: 1200, 1500)
                stats["speed_hist"][bin_speed] += move_time

            # Z-Hop Tespiti (Sadece Z ekseninde yukarı hareket var, XY sabit ve Extrusion yok/negatif)
            if dz > 0 and dx == 0.0 and dy == 0.0 and e_delta <= 0:
                stats["zhop_count"] += 1
                stats["zhop_time_sec"] += move_time

            # Retraction Tespiti (Negatif Extrusion)
            if e_delta < 0:
                stats["retract_count"] += 1
                stats["retract_dist_mm"] += abs(e_delta)
            elif e_delta > 0:
                stats["dist_e_raw"] += e_delta

            # Print (Yazdırma) vs Travel (Boş Hareket) Ayrımı
            if dist > 0:
                if e_delta > 0:
                    stats["print_dist_mm"] += dist
                    stats["print_time_sec"] += move_time
                else:
                    stats["travel_dist_mm"] += dist
                    stats["travel_time_sec"] += move_time

            current_x = new_x
            current_y = new_y
            current_z = new_z
            current_e = (current_e or 0.0) + e_delta if relative_extrusion else params.get("E", current_e)

        # Eğer slicer katman yorumu bırakmamışsa z yüksekliklerinden layer sayısını tahmin et
        if stats["layer_count"] == 0:
            stats["layer_count"] = len([z for z in z_layer_values if z > 0])

        # Hacim ve Ağırlık Hesaplamaları
        filament_radius_mm = filament_diameter / 2
        filament_area_mm2 = math.pi * filament_radius_mm * filament_radius_mm
        filament_volume_cm3 = (stats["dist_e_raw"] * filament_area_mm2) / 1000

        total_time_sec = stats["print_time_sec"] + stats["travel_time_sec"]
        total_dist_mm = stats["print_dist_mm"] + stats["travel_dist_mm"]

        return {
            "total_lines": stats["total_lines"],
            "movement_count": stats["movement_count"],
            "layer_count": stats["layer_count"],
            "print_time_sec": stats["print_time_sec"],
            "travel_time_sec": stats["travel_time_sec"],
            "total_time_text": self.format_duration(total_time_sec),
            "print_dist_mm": stats["print_dist_mm"],
            "travel_dist_mm": stats["travel_dist_mm"],
            "total_dist_mm": total_dist_mm,
            "retract_count": stats["retract_count"],
            "retract_dist_mm": stats["retract_dist_mm"],
            "zhop_count": stats["zhop_count"],
            "zhop_time_sec": stats["zhop_time_sec"],
            "dist_x": stats["dist_x"],
            "dist_y": stats["dist_y"],
            "dist_z": stats["dist_z"],
            "filament_used_m": stats["dist_e_raw"] / 1000,
            "filament_weight_g": filament_volume_cm3 * filament_density,
            "avg_speed": total_dist_mm / (total_time_sec / 60) if total_time_sec > 0 else 0,
            "avg_print_speed": stats["print_dist_mm"] / (stats["print_time_sec"] / 60) if stats["print_time_sec"] > 0 else 0,
            "avg_travel_speed": stats["travel_dist_mm"] / (stats["travel_time_sec"] / 60) if stats["travel_time_sec"] > 0 else 0,
            "max_feedrate": max(stats["f_values"]) if stats["f_values"] else 0,
            "nozzle_temps": sorted(list(stats["nozzle_temps"])),
            "bed_temps": sorted(list(stats["bed_temps"])),
            "speed_hist": dict(sorted(stats["speed_hist"].items()))
        }

    def analyze_structure(self, path: str):
        lines = self.read_file(path)

        structure = {
            "total_lines": len(lines),
            "has_units_mm": False,
            "has_absolute_positioning": False,
            "has_relative_positioning": False,
            "has_home": False,
            "has_nozzle_temp_set": False,
            "has_nozzle_temp_wait": False,
            "has_bed_temp_set": False,
            "has_bed_temp_wait": False,
            "has_extrusion_mode": False,
            "extrusion_mode": None,
            "first_movement_line": None,
            "has_end_nozzle_off": False,
            "has_end_bed_off": False,
            "has_fan_off": False,
            "has_motors_off": False,
            "has_klipper_start": False, # KLIPPER DESTEĞİ
            "has_klipper_end": False    # KLIPPER DESTEĞİ
        }

        for idx, raw_line in enumerate(lines, start=1):
            line = raw_line.strip()
            code_part = line.split(";")[0].strip()

            if not code_part:
                continue

            parts = code_part.split()
            command = parts[0].upper()
            params = self.parse_params(code_part)

            # Klipper Makrolarının Tespiti
            if command in {"PRINT_START", "START_PRINT", "PRIME_LINE"}:
                structure["has_klipper_start"] = True
            elif command in {"PRINT_END", "END_PRINT", "CANCEL_PRINT"}:
                structure["has_klipper_end"] = True

            elif command == "G21":
                structure["has_units_mm"] = True
            elif command == "G28":
                structure["has_home"] = True
            elif command == "M82":
                structure["has_extrusion_mode"] = True
                structure["extrusion_mode"] = "Absolute (M82)"
            elif command == "M83":
                structure["has_extrusion_mode"] = True
                structure["extrusion_mode"] = "Relative (M83)"
            elif command == "M104":
                structure["has_nozzle_temp_set"] = True
                if params.get("S") == 0:
                    structure["has_end_nozzle_off"] = True
            elif command == "M109":
                structure["has_nozzle_temp_wait"] = True
                structure["has_nozzle_temp_set"] = True
            elif command == "M140":
                structure["has_bed_temp_set"] = True
                if params.get("S") == 0:
                    structure["has_end_bed_off"] = True
            elif command == "M190":
                structure["has_bed_temp_wait"] = True
                structure["has_bed_temp_set"] = True
            elif command == "M107":
                structure["has_fan_off"] = True
            elif command in {"M84", "M18"}:
                structure["has_motors_off"] = True
            elif command in {"G0", "G1", "G2", "G3"}:
                if structure["first_movement_line"] is None:
                    structure["first_movement_line"] = idx

        # Klipper mantığına göre uyarı seviyelerini eziyoruz (Override)
        # Eğer PRINT_START makrosu varsa, G28 veya Isıtma komutlarının olmaması HATA değil INFO'dur.
        home_status = "INFO" if structure["has_klipper_start"] and not structure["has_home"] else ("OK" if structure["has_home"] else "ERROR")
        noz_status = "INFO" if structure["has_klipper_start"] and not structure["has_nozzle_temp_set"] else ("OK" if structure["has_nozzle_temp_set"] else "ERROR")
        bed_status = "INFO" if structure["has_klipper_start"] and not structure["has_bed_temp_set"] else ("OK" if structure["has_bed_temp_set"] else "WARNING")
        
        noff_status = "INFO" if structure["has_klipper_end"] and not structure["has_end_nozzle_off"] else ("OK" if structure["has_end_nozzle_off"] else "WARNING")
        boff_status = "INFO" if structure["has_klipper_end"] and not structure["has_end_bed_off"] else ("OK" if structure["has_end_bed_off"] else "WARNING")

        start_checks = []
        if structure["has_klipper_start"]:
            start_checks.append({
                "name": "Klipper Start Macro",
                "status": "INFO",
                "message": self.tr("str_klip_start")
            })
            
        start_checks.extend([
            {
                "name": "G21 (Units)",
                "status": "OK" if structure["has_units_mm"] else "WARNING",
                "message": self.tr("str_g21_ok") if structure["has_units_mm"] else self.tr("str_g21_warn"),
            },
            {
                "name": "G28 (Home)",
                "status": home_status,
                "message": self.tr("str_g28_ok") if structure["has_home"] else self.tr("str_g28_err"),
            },
            {
                "name": "Nozzle Set",
                "status": noz_status,
                "message": self.tr("str_noz_ok") if structure["has_nozzle_temp_set"] else self.tr("str_noz_err"),
            },
            {
                "name": "Nozzle Wait",
                "status": "OK" if structure["has_nozzle_temp_wait"] else "INFO",
                "message": self.tr("str_noz_wait_ok") if structure["has_nozzle_temp_wait"] else self.tr("str_noz_wait_warn"),
            },
            {
                "name": "Bed Set",
                "status": bed_status,
                "message": self.tr("str_bed_ok") if structure["has_bed_temp_set"] else self.tr("str_bed_warn"),
            },
            {
                "name": "Bed Wait",
                "status": "OK" if structure["has_bed_temp_wait"] else "INFO",
                "message": self.tr("str_bed_wait_ok") if structure["has_bed_temp_wait"] else self.tr("str_bed_wait_info"),
            },
            {
                "name": "Extrusion Mode",
                "status": "OK" if structure["has_extrusion_mode"] else "WARNING",
                "message": structure["extrusion_mode"] if structure["has_extrusion_mode"] else self.tr("str_ext_warn"),
            },
            {
                "name": "First Move",
                "status": "OK" if structure["first_movement_line"] else "ERROR",
                "message": f"Line {structure['first_movement_line']}" if structure["first_movement_line"] else self.tr("str_first_err"),
            },
        ])

        end_checks = []
        if structure["has_klipper_end"]:
            end_checks.append({
                "name": "Klipper End Macro",
                "status": "INFO",
                "message": self.tr("str_klip_end")
            })

        end_checks.extend([
            {
                "name": "Nozzle Off",
                "status": noff_status,
                "message": self.tr("str_noff_ok") if structure["has_end_nozzle_off"] else self.tr("str_noff_warn"),
            },
            {
                "name": "Bed Off",
                "status": boff_status,
                "message": self.tr("str_boff_ok") if structure["has_end_bed_off"] else self.tr("str_boff_warn"),
            },
            {
                "name": "Fan Off",
                "status": "OK" if structure["has_fan_off"] else "INFO",
                "message": self.tr("str_fan_ok") if structure["has_fan_off"] else self.tr("str_fan_info"),
            },
            {
                "name": "Motors Off",
                "status": "OK" if structure["has_motors_off"] else "INFO",
                "message": self.tr("str_mot_ok") if structure["has_motors_off"] else self.tr("str_mot_info"),
            },
        ])

        all_checks = start_checks + end_checks

        if any(check["status"] == "ERROR" for check in all_checks):
            summary_status = "ERROR"
        elif any(check["status"] == "WARNING" for check in all_checks):
            summary_status = "WARNING"
        else:
            summary_status = "OK"

        return {
            "start_checks": start_checks,
            "end_checks": end_checks,
            "summary_status": summary_status
        }

    def check(self, path: str) -> List[Issue]:
        issues: List[Issue] = []
        lines = self.read_file(path)

        previous_x: Optional[float] = None
        previous_y: Optional[float] = None
        previous_z: Optional[float] = None
        previous_e: Optional[float] = None

        movement_count = 0
        total_lines = len(lines)

        if total_lines < 50:
            issues.append(Issue(0, "WARNING", self.tr("short_file"), ""))

        for idx, raw_line in enumerate(lines, start=1):
            line = raw_line.strip()

            if "\x00" in raw_line:
                issues.append(Issue(idx, "ERROR", self.tr("null_byte"), raw_line[:120]))

            code_part = line.split(";")[0].strip()
            if not code_part:
                continue

            parts = code_part.split()
            command = parts[0].upper()

            valid_command_pattern = re.match(r"^[A-Z_][A-Z0-9_]*$", command)
            if not valid_command_pattern:
                issues.append(Issue(idx, "WARNING", self.tr("bad_format"), line))
                continue

            params = self.parse_params(code_part)

            if command in {"G0", "G1", "G2", "G3"}:
                movement_count += 1

                x = params.get("X", previous_x)
                y = params.get("Y", previous_y)
                z = params.get("Z", previous_z)
                e = params.get("E", previous_e)
                f = params.get("F")

                if x is not None and not (-self.tolerance <= x <= self.bed_x + self.tolerance):
                    issues.append(Issue(idx, "WARNING", f"{self.tr('x_out')}: X={x}", line))

                if y is not None and not (-self.tolerance <= y <= self.bed_y + self.tolerance):
                    issues.append(Issue(idx, "WARNING", f"{self.tr('y_out')}: Y={y}", line))

                if z is not None and not (-1 <= z <= self.max_z + self.tolerance):
                    issues.append(Issue(idx, "WARNING", f"{self.tr('z_out')}: Z={z}", line))

                # End / Park komutları sırasında zıplamaları hata olarak görmemek için basit bir filtre
                is_end_move = (idx / total_lines) > 0.95
                
                if not is_end_move:
                    if previous_x is not None and x is not None and abs(x - previous_x) > 180:
                        issues.append(Issue(idx, "WARNING", f"{self.tr('jump_x')}: {previous_x} -> {x}", line))

                    if previous_y is not None and y is not None and abs(y - previous_y) > 180:
                        issues.append(Issue(idx, "WARNING", f"{self.tr('jump_y')}: {previous_y} -> {y}", line))

                    if previous_z is not None and z is not None and abs(z - previous_z) > 20:
                        issues.append(Issue(idx, "WARNING", f"{self.tr('jump_z')}: {previous_z} -> {z}", line))

                if f is not None:
                    if f <= 0:
                        issues.append(Issue(idx, "ERROR", f"{self.tr('f_zero')}: F={f}", line))
                    elif f > 30000:
                        issues.append(Issue(idx, "WARNING", f"{self.tr('f_high')}: F={f}", line))

                if previous_e is not None and e is not None:
                    e_delta = e - previous_e
                    if abs(e_delta) > 50:
                        issues.append(Issue(idx, "WARNING", f"{self.tr('e_jump')}: {previous_e} -> {e}", line))

                previous_x = x
                previous_y = y
                previous_z = z
                previous_e = e

            if command in {"M2", "M30"}:
                if (idx / total_lines) < 0.95:
                    issues.append(Issue(idx, "ERROR", self.tr("early_end"), line))

        if movement_count == 0:
            issues.append(Issue(0, "ERROR", self.tr("no_move"), ""))

        return issues