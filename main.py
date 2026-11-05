import os
import sys

from views.applogin import LoginApp
from views.ui_helpers import notify_navigation_ready


def abrir_pantalla_empaquetada(argumentos):
    if len(argumentos) < 2 or argumentos[0] != '--screen':
        return False

    pantalla, *extras = argumentos[1:]
    if pantalla == 'home.py':
        if extras:
            os.environ['GI_USUARIO'] = extras[0]
        from views.home import AppGestiónInstitucional
        app = AppGestiónInstitucional()
    elif pantalla == 'folio_reservado.py':
        from views.folio_reservado import PantallaFolio
        app = PantallaFolio(extras[0] if extras else '')
    elif pantalla == 'crear_documento.py':
        from views.crear_documento import CrearDocumentoApp
        app = CrearDocumentoApp(extras[0] if extras else '')
    elif pantalla == 'update.py':
        from views.update import DashboardApp
        app = DashboardApp()
    else:
        raise ValueError(f'Pantalla empaquetada no reconocida: {pantalla}')
    app.update_idletasks()
    app.update()
    notify_navigation_ready()
    app.mainloop()
    return True


if __name__ == "__main__":
    if not abrir_pantalla_empaquetada(sys.argv[1:]):
        app = LoginApp()
        app.mainloop()