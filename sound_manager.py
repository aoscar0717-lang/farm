"""
夜巡農場 (Nightwatch Farm) - 音效與聲音合成管理器
"""

import math
import struct
import pygame
from typing import Dict, Optional
from game_config import EventType, GameEvent


class SoundManager:
    """音效管理器：支援真實檔案載入與自帶合成音效"""

    def __init__(self, sfx_enabled: bool = True):
        self.sfx_enabled = sfx_enabled
        self.sounds: Dict[str, Optional[pygame.mixer.Sound]] = {}
        self.bgm_channel = None
        # 只靜音背景音樂，音效 (採收/建造/UI 點擊等) 不受影響 -- 跟
        # sfx_enabled 是兩個獨立開關：sfx_enabled 是音訊裝置整個初始化
        # 失敗時的保護，music_muted 是玩家在暫停選單自己選的偏好。
        self.music_muted = False
        
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
        except Exception as e:
            print(f"[SoundManager] 無法初始化音訊設備: {e}")
            self.sfx_enabled = False
            return

        if self.sfx_enabled:
            self._init_sounds()

    def _generate_tone(self, freq: float, duration: float, volume: float = 0.4, wave_type: str = "sine") -> pygame.mixer.Sound:
        sample_rate = 22050
        n_samples = int(sample_rate * duration)
        buf = bytearray()

        for i in range(n_samples):
            t = i / sample_rate
            envelope = max(0.0, 1.0 - (i / n_samples))
            
            if wave_type == "sine":
                val = math.sin(2.0 * math.pi * freq * t)
            elif wave_type == "square":
                val = 1.0 if math.sin(2.0 * math.pi * freq * t) > 0 else -1.0
            elif wave_type == "saw":
                val = 2.0 * (t * freq - math.floor(0.5 + t * freq))
            elif wave_type == "noise":
                import random
                val = random.uniform(-1.0, 1.0)
            elif wave_type == "chirp":
                cur_freq = freq * (1.0 + (i / n_samples) * 1.5)
                val = math.sin(2.0 * math.pi * cur_freq * t)
            else:
                val = math.sin(2.0 * math.pi * freq * t)

            sample = int(val * envelope * volume * 32767)
            sample = max(-32768, min(32767, sample))
            data = struct.pack("<hh", sample, sample)
            buf.extend(data)

        return pygame.mixer.Sound(buffer=bytes(buf))


    def play_bgm(self, is_day: bool):
        if not self.sfx_enabled: return
        import os
        
        bgm_file = "assets/bgm_day.mp3" if is_day else "assets/bgm_night.mp3"
        fallback_file = "assets/bgm_day.ogg" if is_day else "assets/bgm_night.ogg"
        
        if os.path.exists(bgm_file):
            try:
                pygame.mixer.music.load(bgm_file)
                pygame.mixer.music.play(loops=-1)
                # 切換日夜音樂會重新 load()+play()，音量預設會回到 100%，
                # 所以每次播放都要重新套用一次玩家的靜音偏好，不然靜音
                # 狀態撐不過日夜切換。
                pygame.mixer.music.set_volume(0.0 if self.music_muted else 1.0)
            except Exception as e:
                print(f"[SoundManager] BGM Error: {e}")
        elif os.path.exists(fallback_file):
            try:
                pygame.mixer.music.load(fallback_file)
                pygame.mixer.music.play(loops=-1)
                pygame.mixer.music.set_volume(0.0 if self.music_muted else 1.0)
            except Exception as e:
                print(f"[SoundManager] BGM Error: {e}")
        else:
            pass

    def toggle_music_mute(self) -> bool:
        """切換背景音樂靜音狀態，回傳切換後的結果 (True=已靜音)。
        用 set_volume 而不是暫停/停止播放，音樂會繼續在背景播放、
        取消靜音時立刻接得回來，不會從頭重播或卡頓。"""
        self.music_muted = not self.music_muted
        try:
            pygame.mixer.music.set_volume(0.0 if self.music_muted else 1.0)
        except Exception:
            pass
        return self.music_muted

    def _init_sounds(self):
        try:
            self.sounds["plant"] = self._generate_tone(350, 0.08, volume=0.3, wave_type="sine")
            self.sounds["harvest"] = self._generate_tone(587.33, 0.15, volume=0.4, wave_type="chirp")
            self.sounds["water"] = self._generate_tone(660.0, 0.12, volume=0.35, wave_type="sine")
            self.sounds["gold"] = self._generate_tone(880.0, 0.1, volume=0.3, wave_type="sine")
            self.sounds["build"] = self._generate_tone(220.0, 0.12, volume=0.4, wave_type="square")
            self.sounds["trap"] = self._generate_tone(120.0, 0.25, volume=0.6, wave_type="noise")
            self.sounds["scare"] = self._generate_tone(400.0, 0.2, volume=0.4, wave_type="chirp")
            self.sounds["bark"] = self._generate_tone(440.0, 0.1, volume=0.5, wave_type="saw")
            self.sounds["bite"] = self._generate_tone(200.0, 0.1, volume=0.5, wave_type="square")
            self.sounds["level_up"] = self._generate_tone(659.25, 0.4, volume=0.5, wave_type="chirp")
            self.sounds["destroy"] = self._generate_tone(90.0, 0.35, volume=0.5, wave_type="noise")
            self.sounds["stolen"] = self._generate_tone(261.63, 0.2, volume=0.4, wave_type="saw")
            self.sounds["game_over"] = self._generate_tone(110.0, 0.8, volume=0.6, wave_type="square")
            self.sounds["night_alarm"] = self._generate_tone(493.88, 0.3, volume=0.4, wave_type="sine")
            self.sounds["error"] = self._generate_tone(160.0, 0.14, volume=0.35, wave_type="square")
            # 通用 UI 點擊音（切換分頁、選取工具卡片...），要短促清脆、
            # 跟「plant」那種比較柔和的種植音區分開，音量壓低一點避免
            # 頻繁點擊時太吵。
            self.sounds["ui_click"] = self._generate_tone(1000.0, 0.05, volume=0.22, wave_type="sine")
            self.bgm_channel = None

        except Exception as e:
            print(f"[SoundManager] 合成音效失敗: {e}")

    def play(self, sound_name: str):
        if not self.sfx_enabled:
            return
        snd = self.sounds.get(sound_name)
        if snd:
            try:
                snd.play()
            except Exception:
                pass

    def handle_game_event(self, event: GameEvent):
        t = event.event_type
        if t == EventType.CROP_PLANTED:
            self.play("plant")
        elif t == EventType.CROP_HARVESTED:
            self.play("harvest")
        elif t == EventType.CROP_WATERED:
            self.play("water")
        elif t == EventType.DECORATION_PLACED or t == EventType.DEFENSE_PLACED:
            self.play("build")
        elif t == EventType.PET_BOUGHT:
            self.play("build")
        elif t == EventType.CAT_BONUS:
            self.play("gold")
        elif t == EventType.FARM_LEVEL_UP:
            self.play("level_up")
        elif t == EventType.FARM_LEVEL_DOWN:
            self.play("destroy")
        elif t == EventType.TRAP_TRIGGERED:
            self.play("trap")
        elif t == EventType.SCARECROW_SCARE:
            self.play("scare")
        elif t == EventType.DOG_BARK:
            self.play("bark")
        elif t == EventType.DOG_ATTACK:
            self.play("bite")
        elif t == EventType.BLOOD_MOON_WARNING:
            self.play("night_alarm")
        elif t == EventType.ENEMY_STUNNED:
            self.play("trap")
        elif t == EventType.BEE_ATTACK:
            self.play("plant")
        elif t == EventType.DOG_WHISTLE:
            self.play("scare")
        elif t == EventType.DAILY_TAX_PAID:
            self.play("gold")
        elif t == EventType.PROSPERITY_DIVIDEND:
            self.play("gold")
        elif t == EventType.VAULT_RAIDED:
            self.play("stolen")
        elif t == EventType.ORDER_FULFILLED:
            self.play("gold")
        elif t == EventType.ORDERS_GENERATED:
            self.play("ui_click")
        elif t == EventType.CROP_STOLEN:
            self.play("stolen")
        elif t == EventType.DAY_STARTED:
            self.play_bgm(is_day=True)
        elif t == EventType.NIGHT_STARTED:
            self.play_bgm(is_day=False)
            self.play("night_alarm")
        elif t == EventType.GAME_OVER:
            self.play("game_over")
