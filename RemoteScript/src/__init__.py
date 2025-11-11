r"""
__init__.py - Entry point for Faderfox MX12 Custom Control Surface

Place this file and FaderfoxMX12byYVMA.py in:
Mac: ~/Music/Ableton/User Library/Remote Scripts/FaderfoxMX12byYVMA/
Windows: %USERPROFILE%\Documents\Ableton\User Library\Remote Scripts\FaderfoxMX12byYVMA\
"""

from .FaderfoxMX12byYVMA import FaderfoxMX12byYVMA


def create_instance(c_instance):
    """Entry point appelé par Ableton Live"""
    return FaderfoxMX12byYVMA(c_instance)