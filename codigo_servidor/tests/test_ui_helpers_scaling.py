import unittest
from unittest.mock import MagicMock, patch

from views.ui_helpers import window_setup


class WindowSetupScalingTests(unittest.TestCase):
    @patch('views.ui_helpers.ctk.set_widget_scaling')
    @patch('views.ui_helpers.ctk.set_window_scaling')
    @patch('views.ui_helpers.ctk.ScalingTracker.get_window_dpi_scaling', return_value=1.0)
    def test_full_hd_window_uses_larger_ui_and_target_dimensions(
        self, _dpi, set_window_scaling, set_widget_scaling,
    ):
        window = MagicMock()
        window.winfo_screenwidth.return_value = 1920
        window.winfo_screenheight.return_value = 1080

        window_setup(window, 'test')

        set_widget_scaling.assert_called_once_with(1.2)
        set_window_scaling.assert_called_once_with(1.2)
        window.geometry.assert_called_with('1920x1080+0+0')
        window.maxsize.assert_called_with(1920, 1080)

    @patch('views.ui_helpers.ctk.set_widget_scaling')
    @patch('views.ui_helpers.ctk.set_window_scaling')
    @patch('views.ui_helpers.ctk.ScalingTracker.get_window_dpi_scaling', return_value=1.0)
    def test_smaller_screen_keeps_window_inside_display_and_scales_up(
        self, _dpi, set_window_scaling, set_widget_scaling,
    ):
        window = MagicMock()
        window.winfo_screenwidth.return_value = 1536
        window.winfo_screenheight.return_value = 960

        window_setup(window, 'test')

        set_widget_scaling.assert_called_once_with(1.15)
        set_window_scaling.assert_called_once_with(1.15)
        window.geometry.assert_called_with('1536x960+0+0')
        window.maxsize.assert_called_with(1536, 960)


if __name__ == '__main__':
    unittest.main()
