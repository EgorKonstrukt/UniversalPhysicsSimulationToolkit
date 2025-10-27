import pygame

class SoundManager:
    """
    Manages all sound loading and playback.
    """

    def __init__(self):
        pygame.mixer.init()
    #     self.sounds = {
    #         'click': pygame.mixer.Sound("../../sounds/gui/click.mp3"),
    #         'click_2': pygame.mixer.Sound("../../sounds/gui/click_2.mp3"),
    #         'click_3': pygame.mixer.Sound("../../sounds/gui/click_3.mp3"),
    #         'click_4': pygame.mixer.Sound("../../sounds/gui/click_4.mp3"),
    #         'hover': pygame.mixer.Sound("../../sounds/gui/hovering.mp3"),
    #         'error': pygame.mixer.Sound("../../sounds/gui/error.mp3"),
    #         'spawn': pygame.mixer.Sound("../../sounds/spawn.mp3"),
    #         'slider': pygame.mixer.Sound("../../sounds/gui/slider.mp3"),
    #         'beep_1': pygame.mixer.Sound("../../sounds/gui/beep_1.mp3"),
    #         'pause': pygame.mixer.Sound("../../sounds/pause.mp3"),
    #         'pause_in': pygame.mixer.Sound("../../sounds/pause_in.mp3"),
    #         'close': pygame.mixer.Sound("../../sounds/close.mp3"),
    #         'screenshot': pygame.mixer.Sound("../../sounds/gui/screenshot.mp3"),
    #         'save_done': pygame.mixer.Sound("../../sounds/gui/save_done.mp3"),
    #         'load_error': pygame.mixer.Sound("../../sounds/gui/save_error.mp3")
    #     }
    #     self.set_volumes()
    #
    # def set_volumes(self):
    #     self.sounds['beep_1'].set_volume(0.2)
    #     self.sounds['spawn'].set_volume(0.2)
    #     self.sounds['hover'].set_volume(0.01)
    #
    def play(self, sound_name):
        pass
        # if sound_name in self.sounds:
        #     self.sounds[sound_name].play()