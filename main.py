import flet as ft
import speedtest
import threading
import time
import datetime
import sqlite3
import math
import os

# --- Configurações de Banco de Dados ---
def get_db_path():
    # Compatível com Android (usa diretório de dados do app)
    data_dir = os.environ.get("FLET_APP_STORAGE_DATA", ".")
    return os.path.join(data_dir, "nettest_history.db")

def init_db():
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            download REAL,
            upload REAL,
            ping INTEGER
        )
    ''')
    conn.commit()
    conn.close()

def save_result(download, upload, ping):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''
        INSERT INTO history (timestamp, download, upload, ping)
        VALUES (?, ?, ?, ?)
    ''', (timestamp, download, upload, ping))
    conn.commit()
    conn.close()

def get_history():
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    cursor.execute('SELECT timestamp, download, upload, ping FROM history ORDER BY id DESC LIMIT 10')
    rows = cursor.fetchall()
    conn.close()
    return rows

def clear_history():
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    cursor.execute('DELETE FROM history')
    conn.commit()
    conn.close()


# --- Velocímetro com ticks e ponteiro aprimorado ---
class Speedometer(ft.UserControl):
    def __init__(self):
        super().__init__()
        self.angle = -math.pi * 0.75
        self.target_angle = self.angle
        self.is_animating = False

    def build(self):
        bg_arc = ft.canvas.Arc(
            0, 0, 200, 200,
            start_angle=-math.pi * 0.75,
            sweep_angle=math.pi * 1.5,
            paint=ft.Paint(
                color="#1c1c1c",
                style=ft.PaintingStyle.STROKE,
                stroke_width=10,
                stroke_cap=ft.StrokeCap.ROUND,
            ),
        )

        self.progress_arc = ft.canvas.Arc(
            0, 0, 200, 200,
            start_angle=-math.pi * 0.75,
            sweep_angle=0,
            paint=ft.Paint(
                color="#2563ff",
                style=ft.PaintingStyle.STROKE,
                stroke_width=10,
                stroke_cap=ft.StrokeCap.ROUND,
            ),
        )

        self.needle = ft.canvas.Line(
            x1=100, y1=100,
            x2=100 + 72 * math.cos(self.angle),
            y2=100 + 72 * math.sin(self.angle),
            paint=ft.Paint(
                color="#2563ff",
                stroke_width=2.5,
                stroke_cap=ft.StrokeCap.ROUND,
            ),
        )

        self.needle_glow = ft.canvas.Line(
            x1=100, y1=100,
            x2=100 + 72 * math.cos(self.angle),
            y2=100 + 72 * math.sin(self.angle),
            paint=ft.Paint(
                color="#5585ff",
                stroke_width=1.0,
                stroke_cap=ft.StrokeCap.ROUND,
            ),
        )

        center_ring = ft.canvas.Circle(
            100, 100, 9,
            paint=ft.Paint(color="#2563ff", style=ft.PaintingStyle.STROKE, stroke_width=2),
        )
        center_fill = ft.canvas.Circle(
            100, 100, 7,
            paint=ft.Paint(color="#0a0a0a", style=ft.PaintingStyle.FILL),
        )
        center_dot = ft.canvas.Circle(
            100, 100, 2.5,
            paint=ft.Paint(color="#2563ff", style=ft.PaintingStyle.FILL),
        )

        tick_shapes = []
        num_ticks = 7
        for i in range(num_ticks):
            frac = i / (num_ticks - 1)
            a = -math.pi * 0.75 + frac * math.pi * 1.5
            inner_r = 82
            outer_r = 90
            x1 = 100 + inner_r * math.cos(a)
            y1 = 100 + inner_r * math.sin(a)
            x2 = 100 + outer_r * math.cos(a)
            y2 = 100 + outer_r * math.sin(a)
            tick_shapes.append(
                ft.canvas.Line(
                    x1=x1, y1=y1, x2=x2, y2=y2,
                    paint=ft.Paint(color="#2a2a2a", stroke_width=1.5, stroke_cap=ft.StrokeCap.ROUND),
                )
            )

        minor_ticks = []
        num_minor = 42
        for i in range(num_minor + 1):
            frac = i / num_minor
            a = -math.pi * 0.75 + frac * math.pi * 1.5
            skip = False
            for j in range(num_ticks):
                fj = j / (num_ticks - 1)
                aj = -math.pi * 0.75 + fj * math.pi * 1.5
                if abs(a - aj) < 0.01:
                    skip = True
                    break
            if skip:
                continue
            inner_r = 86
            outer_r = 90
            x1 = 100 + inner_r * math.cos(a)
            y1 = 100 + inner_r * math.sin(a)
            x2 = 100 + outer_r * math.cos(a)
            y2 = 100 + outer_r * math.sin(a)
            minor_ticks.append(
                ft.canvas.Line(
                    x1=x1, y1=y1, x2=x2, y2=y2,
                    paint=ft.Paint(color="#1e1e1e", stroke_width=1.0, stroke_cap=ft.StrokeCap.ROUND),
                )
            )

        all_shapes = (
            minor_ticks +
            tick_shapes +
            [bg_arc, self.progress_arc, self.needle_glow, self.needle,
             center_fill, center_ring, center_dot]
        )

        self.canvas = ft.canvas.Canvas(
            all_shapes,
            width=200,
            height=200,
        )
        return self.canvas

    def update_speed(self, speed_mbps, max_speed=100):
        speed = min(speed_mbps, max_speed)
        normalized_speed = speed / max_speed
        total_angle_range = math.pi * 1.5
        self.target_angle = (-math.pi * 0.75) + (normalized_speed * total_angle_range)
        if not self.is_animating:
            self.is_animating = True
            threading.Thread(target=self._animate_needle, daemon=True).start()

    def _animate_needle(self):
        step = 0.05
        while abs(self.angle - self.target_angle) > step:
            if self.angle < self.target_angle:
                self.angle += step
            else:
                self.angle -= step
            nx = 100 + 72 * math.cos(self.angle)
            ny = 100 + 72 * math.sin(self.angle)
            self.needle.x2 = nx
            self.needle.y2 = ny
            self.needle_glow.x2 = nx
            self.needle_glow.y2 = ny
            self.progress_arc.sweep_angle = self.angle - (-math.pi * 0.75)
            self.update()
            time.sleep(0.01)

        self.angle = self.target_angle
        nx = 100 + 72 * math.cos(self.angle)
        ny = 100 + 72 * math.sin(self.angle)
        self.needle.x2 = nx
        self.needle.y2 = ny
        self.needle_glow.x2 = nx
        self.needle_glow.y2 = ny
        self.progress_arc.sweep_angle = self.angle - (-math.pi * 0.75)
        self.update()
        self.is_animating = False


# --- App Principal ---
def main(page: ft.Page):
    page.title = "NetTest Professional"
    page.bgcolor = "#0a0a0a"
    page.padding = ft.padding.symmetric(horizontal=20, vertical=24)
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.theme_mode = ft.ThemeMode.DARK

    COR_FUNDO       = "#0a0a0a"
    COR_CARD        = "#111111"
    COR_CARD_ALT    = "#0f0f0f"
    COR_AZUL        = "#2563ff"
    COR_AZUL_SUAVE  = "#5585ff"
    COR_BORDA       = "#1c1c1c"
    COR_BORDA_SUTIL = "#161616"
    COR_TEXTO       = ft.colors.WHITE
    COR_SUBTEXTO    = "#555555"
    COR_DOWNLOAD    = "#22c55e"
    COR_UPLOAD      = "#ef4444"

    init_db()

    is_testing = False
    st_instance = None

    titulo = ft.Text(
        "NetTest",
        size=28,
        color=COR_AZUL,
        weight=ft.FontWeight.BOLD,
        opacity=0,
        animate_opacity=ft.animation.Animation(800, ft.AnimationCurve.EASE_OUT),
    )
    subtitulo = ft.Text(
        "P R O F E S S I O N A L",
        size=10,
        color=COR_SUBTEXTO,
        weight=ft.FontWeight.W_500,
        opacity=0,
        animate_opacity=ft.animation.Animation(1000, ft.AnimationCurve.EASE_OUT),
    )

    header = ft.Column(
        [titulo, ft.Container(height=2), subtitulo],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=0,
    )

    velocimetro = Speedometer()

    display_valor = ft.Text(
        "0.0",
        size=44,
        color=COR_TEXTO,
        weight=ft.FontWeight.BOLD,
    )
    display_unidade = ft.Text(
        "Mbps",
        size=11,
        color=COR_SUBTEXTO,
        weight=ft.FontWeight.W_500,
    )
    fase_teste = ft.Text(
        "AGUARDANDO",
        size=10,
        color=COR_AZUL,
        weight=ft.FontWeight.W_600,
    )

    stack_medidor = ft.Stack(
        controls=[
            velocimetro,
            ft.Container(
                content=ft.Column(
                    [display_valor, ft.Container(height=2), display_unidade, ft.Container(height=6), fase_teste],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=0,
                ),
                width=200,
                height=200,
                alignment=ft.alignment.center,
                padding=ft.padding.only(top=20),
            ),
        ]
    )

    container_medidor = ft.Container(
        content=stack_medidor,
        width=240,
        height=240,
        bgcolor=COR_CARD,
        border_radius=120,
        border=ft.Border(
            top=ft.BorderSide(1.5, COR_BORDA),
            right=ft.BorderSide(1.5, COR_BORDA),
            bottom=ft.BorderSide(1.5, COR_BORDA),
            left=ft.BorderSide(1.5, COR_BORDA),
        ),
        alignment=ft.alignment.center,
        animate_opacity=ft.animation.Animation(400, ft.AnimationCurve.EASE_OUT),
    )

    def _make_stat_pill(icone_nome, cor_icone, controle_valor, label_str):
        return ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [ft.Icon(icone_nome, size=13, color=cor_icone)],
                        spacing=4,
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                    controle_valor,
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=4,
            ),
            bgcolor=COR_CARD,
            border_radius=14,
            padding=ft.padding.symmetric(horizontal=12, vertical=12),
            expand=True,
            border=ft.Border(
                top=ft.BorderSide(1, COR_BORDA),
                right=ft.BorderSide(1, COR_BORDA),
                bottom=ft.BorderSide(1, COR_BORDA),
                left=ft.BorderSide(1, COR_BORDA),
            ),
            opacity=0,
            animate_opacity=ft.animation.Animation(500, ft.AnimationCurve.EASE_OUT),
            offset=ft.transform.Offset(0, 0.4),
            animate_offset=ft.animation.Animation(500, ft.AnimationCurve.DECELERATE),
        )

    txt_download = ft.Row(
        [
            ft.Text("0.0", size=22, color=COR_TEXTO, weight=ft.FontWeight.BOLD),
            ft.Text("Mbps", size=10, color=COR_SUBTEXTO, weight=ft.FontWeight.W_500),
        ],
        spacing=3,
        alignment=ft.MainAxisAlignment.CENTER,
        vertical_alignment=ft.CrossAxisAlignment.END,
    )
    txt_upload = ft.Row(
        [
            ft.Text("0.0", size=22, color=COR_TEXTO, weight=ft.FontWeight.BOLD),
            ft.Text("Mbps", size=10, color=COR_SUBTEXTO, weight=ft.FontWeight.W_500),
        ],
        spacing=3,
        alignment=ft.MainAxisAlignment.CENTER,
        vertical_alignment=ft.CrossAxisAlignment.END,
    )

    val_download = txt_download.controls[0]
    val_upload   = txt_upload.controls[0]

    pill_download = _make_stat_pill(ft.icons.ARROW_DOWNWARD_ROUNDED, COR_DOWNLOAD, txt_download, "DOWNLOAD")
    pill_upload   = _make_stat_pill(ft.icons.ARROW_UPWARD_ROUNDED, COR_UPLOAD, txt_upload, "UPLOAD")

    linha_pills = ft.Row([pill_download, pill_upload], spacing=10)

    val_ping_num = ft.Text("0", size=20, color=COR_TEXTO, weight=ft.FontWeight.BOLD)
    val_ping_ms  = ft.Text(" ms", size=12, color=COR_SUBTEXTO, weight=ft.FontWeight.W_500)

    tira_ping = ft.Container(
        content=ft.Row(
            [
                ft.Row(spacing=6, alignment=ft.MainAxisAlignment.START),
                ft.Row(
                    [val_ping_num, val_ping_ms],
                    spacing=0,
                    alignment=ft.MainAxisAlignment.END,
                    vertical_alignment=ft.CrossAxisAlignment.END,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=COR_CARD,
        border_radius=12,
        padding=ft.padding.symmetric(horizontal=16, vertical=12),
        border=ft.Border(
            top=ft.BorderSide(1, COR_BORDA),
            right=ft.BorderSide(1, COR_BORDA),
            bottom=ft.BorderSide(1, COR_BORDA),
            left=ft.BorderSide(1, COR_BORDA),
        ),
        opacity=0,
        animate_opacity=ft.animation.Animation(500, ft.AnimationCurve.EASE_OUT),
        offset=ft.transform.Offset(0, 0.4),
        animate_offset=ft.animation.Animation(500, ft.AnimationCurve.DECELERATE),
    )

    anel_progresso = ft.ProgressRing(
        width=18, height=18, stroke_width=2,
        color=COR_AZUL, visible=False,
    )
    texto_btn = ft.Text(
        "INICIAR TESTE",
        color=COR_TEXTO,
        weight=ft.FontWeight.W_600,
        size=12,
    )
    btn_content = ft.Stack(
        [
            ft.Container(content=texto_btn, alignment=ft.alignment.center),
            ft.Container(content=anel_progresso, alignment=ft.alignment.center),
        ],
        width=180,
        height=46,
    )
    btn_iniciar = ft.Container(
        content=btn_content,
        alignment=ft.alignment.center,
        width=180,
        height=46,
        bgcolor=ft.colors.TRANSPARENT,
        border=ft.Border(
            top=ft.BorderSide(1.5, COR_AZUL),
            right=ft.BorderSide(1.5, COR_AZUL),
            bottom=ft.BorderSide(1.5, COR_AZUL),
            left=ft.BorderSide(1.5, COR_AZUL),
        ),
        border_radius=23,
        animate_scale=ft.animation.Animation(250, ft.AnimationCurve.BOUNCE_OUT),
        on_click=None,
    )

    lista_historico = ft.ListView(expand=True, spacing=6, padding=0)

    def atualizar_view_historico():
        lista_historico.controls.clear()
        dados = get_history()
        for row in dados:
            ts, down, up, ping = row
            dt_obj = datetime.datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
            data_str = dt_obj.strftime("%d/%m")
            hora_str = dt_obj.strftime("%H:%M")

            lista_historico.controls.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Column(
                                [
                                    ft.Text(data_str, size=12, color=COR_TEXTO, weight=ft.FontWeight.W_600),
                                    ft.Text(hora_str, size=10, color=COR_SUBTEXTO),
                                ],
                                alignment=ft.MainAxisAlignment.CENTER,
                                spacing=1,
                            ),
                            ft.Container(width=1, height=28, bgcolor=COR_BORDA),
                            ft.Row(
                                [
                                    ft.Icon(ft.icons.ARROW_DOWNWARD_ROUNDED, size=12, color=COR_DOWNLOAD),
                                    ft.Text(f"{down:.1f}", size=14, color=COR_TEXTO, weight=ft.FontWeight.W_600),
                                ],
                                spacing=3,
                            ),
                            ft.Row(
                                [
                                    ft.Icon(ft.icons.ARROW_UPWARD_ROUNDED, size=12, color=COR_UPLOAD),
                                    ft.Text(f"{up:.1f}", size=14, color=COR_TEXTO, weight=ft.FontWeight.W_600),
                                ],
                                spacing=3,
                            ),
                            ft.Container(expand=True),
                            ft.Text(f"{ping} ms", size=11, color=COR_SUBTEXTO),
                        ],
                        spacing=10,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    bgcolor=COR_CARD_ALT,
                    border_radius=10,
                    padding=ft.padding.symmetric(horizontal=14, vertical=10),
                    border=ft.Border(
                        top=ft.BorderSide(1, COR_BORDA_SUTIL),
                        right=ft.BorderSide(1, COR_BORDA_SUTIL),
                        bottom=ft.BorderSide(1, COR_BORDA_SUTIL),
                        left=ft.BorderSide(1, COR_BORDA_SUTIL),
                    ),
                )
            )
        lista_historico.update()

    def on_limpar_historico(e):
        clear_history()
        atualizar_view_historico()

    btn_limpar = ft.TextButton(
        "limpar",
        style=ft.ButtonStyle(color=COR_AZUL, padding=ft.padding.all(0)),
        on_click=on_limpar_historico,
    )

    secao_historico = ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [btn_limpar],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Container(height=8),
                lista_historico,
            ],
            spacing=0,
        ),
        padding=ft.padding.only(top=16),
        expand=True,
        border=ft.Border(top=ft.BorderSide(1, COR_BORDA)),
    )

    def executar_teste(e):
        nonlocal is_testing, st_instance
        if is_testing:
            return
        is_testing = True

        anel_progresso.visible = True
        texto_btn.value = ""
        btn_iniciar.scale = 0.92
        fase_teste.value = "CONECTANDO..."
        fase_teste.color = COR_SUBTEXTO

        val_download.value = "0.0"
        val_upload.value   = "0.0"
        val_ping_num.value = "0"
        display_valor.value = "0.0"
        velocimetro.update_speed(0)

        for ctrl in [pill_download, pill_upload, tira_ping]:
            ctrl.opacity = 0
            ctrl.offset = ft.transform.Offset(0, 0.4)

        page.update()

        def tarefa_teste():
            nonlocal st_instance
            final_down = 0.0
            final_up   = 0.0
            final_ping = 0

            try:
                fase_teste.value = "MEDINDO PING"
                fase_teste.color = "#facc15"
                page.update()

                if st_instance is None:
                    st_instance = speedtest.Speedtest()
                st_instance.get_best_server()
                final_ping = int(st_instance.results.ping)
                val_ping_num.value = str(final_ping)

                tira_ping.opacity = 1
                tira_ping.offset  = ft.transform.Offset(0, 0)
                page.update()
                time.sleep(0.4)

                fase_teste.value = "TESTANDO DOWNLOAD"
                fase_teste.color = COR_DOWNLOAD
                page.update()

                d_raw = st_instance.download()
                final_down = d_raw / 1_000_000

                steps = 25
                max_d = max(100, final_down * 1.2)
                for i in range(steps + 1):
                    sim = (final_down / steps) * i
                    display_valor.value = f"{sim:.1f}"
                    velocimetro.update_speed(sim, max_speed=max_d)
                    page.update()
                    time.sleep(0.018)

                display_valor.value  = f"{final_down:.1f}"
                val_download.value   = f"{final_down:.1f}"
                pill_download.opacity = 1
                pill_download.offset  = ft.transform.Offset(0, 0)
                page.update()
                time.sleep(0.4)

                fase_teste.value = "TESTANDO UPLOAD"
                fase_teste.color = COR_UPLOAD
                page.update()

                velocimetro.update_speed(0)
                display_valor.value = "0.0"
                page.update()
                time.sleep(0.3)

                u_raw = st_instance.upload()
                final_up = u_raw / 1_000_000

                max_u = max(50, final_up * 1.2)
                for i in range(steps + 1):
                    sim = (final_up / steps) * i
                    display_valor.value = f"{sim:.1f}"
                    velocimetro.update_speed(sim, max_speed=max_u)
                    page.update()
                    time.sleep(0.018)

                display_valor.value = f"{final_up:.1f}"
                val_upload.value    = f"{final_up:.1f}"
                pill_upload.opacity = 1
                pill_upload.offset  = ft.transform.Offset(0, 0)

                fase_teste.value = "CONCLUÍDO"
                fase_teste.color = COR_AZUL
                page.update()

                save_result(final_down, final_up, final_ping)
                atualizar_view_historico()

            except Exception as ex:
                display_valor.value = "Erro"
                fase_teste.value = "FALHA"
                fase_teste.color = ft.colors.RED_400
                print(f"Erro no teste: {ex}")
            finally:
                nonlocal is_testing
                is_testing = False
                anel_progresso.visible = False
                texto_btn.value = "INICIAR TESTE"
                btn_iniciar.scale = 1.0
                velocimetro.update_speed(0)
                page.update()

        threading.Thread(target=tarefa_teste, daemon=True).start()

    btn_iniciar.on_click = executar_teste

    page.add(
        ft.Column(
            [
                header,
                ft.Container(height=20),
                container_medidor,
                ft.Container(height=16),
                linha_pills,
                ft.Container(height=10),
                tira_ping,
                ft.Container(height=20),
                btn_iniciar,
                ft.Container(height=24),
                secao_historico,
            ],
            alignment=ft.MainAxisAlignment.START,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True,
            spacing=0,
        )
    )

    page.update()
    time.sleep(0.15)
    titulo.opacity = 1
    subtitulo.opacity = 1
    page.update()

    atualizar_view_historico()


# IMPORTANTE: sem view=WEB_BROWSER para mobile
ft.app(target=main)
