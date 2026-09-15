package com.lucis.tv;

import android.app.Activity;
import android.os.Bundle;
import android.view.KeyEvent;
import android.view.View;
import android.widget.Toast;

import androidx.media3.common.MediaItem;
import androidx.media3.common.PlaybackException;
import androidx.media3.common.Player;
import androidx.media3.common.TrackSelectionParameters;
import androidx.media3.exoplayer.ExoPlayer;
import androidx.media3.ui.PlayerView;

public class PlayerActivity extends Activity {
    private ExoPlayer player;
    private PlayerView playerView;
    private String url;
    private String progressKey;

    @Override protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().getDecorView().setSystemUiVisibility(
                View.SYSTEM_UI_FLAG_FULLSCREEN |
                View.SYSTEM_UI_FLAG_HIDE_NAVIGATION |
                View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY);

        playerView = new PlayerView(this);
        playerView.setUseController(true);
        playerView.setControllerAutoShow(true);
        setContentView(playerView);

        url = getIntent().getStringExtra("url");
        if (url == null || url.trim().isEmpty()) { finish(); return; }
        progressKey = "progress_" + Integer.toHexString(url.hashCode());

        player = new ExoPlayer.Builder(this).build();
        playerView.setPlayer(player);

        TrackSelectionParameters params = player.getTrackSelectionParameters().buildUpon()
                .setPreferredAudioLanguages("yue", "zh-HK", "zh")
                .setPreferredTextLanguages("zh-Hant", "zh-HK", "zh")
                .build();
        player.setTrackSelectionParameters(params);

        player.addListener(new Player.Listener() {
            @Override public void onPlayerError(PlaybackException error) {
                Toast.makeText(PlayerActivity.this, "播放失败：" + error.getErrorCodeName(), Toast.LENGTH_LONG).show();
            }
            @Override public void onPlaybackStateChanged(int state) {
                if (state == Player.STATE_READY) {
                    long saved = getSharedPreferences("lucis", MODE_PRIVATE).getLong(progressKey, 0L);
                    long duration = player.getDuration();
                    if (saved > 30_000 && (duration <= 0 || duration - saved > 60_000)) player.seekTo(saved);
                }
                if (state == Player.STATE_ENDED) clearProgress();
            }
        });
        player.setMediaItem(MediaItem.fromUri(url));
        player.prepare();
        player.play();
    }

    private void saveProgress() {
        if (player == null || progressKey == null) return;
        long pos = player.getCurrentPosition();
        long duration = player.getDuration();
        if (duration > 0 && duration - pos < 60_000) { clearProgress(); return; }
        if (pos > 15_000) {
            getSharedPreferences("lucis", MODE_PRIVATE).edit()
                    .putLong(progressKey, pos)
                    .putLong(progressKey + "_duration", Math.max(duration, 0L))
                    .apply();
        }
    }

    private void clearProgress() {
        if (progressKey != null) getSharedPreferences("lucis", MODE_PRIVATE).edit()
                .remove(progressKey).remove(progressKey + "_duration").apply();
    }

    @Override public boolean onKeyDown(int keyCode, KeyEvent event) {
        if (keyCode == KeyEvent.KEYCODE_DPAD_CENTER || keyCode == KeyEvent.KEYCODE_ENTER) {
            if (playerView.isControllerFullyVisible()) playerView.hideController(); else playerView.showController();
            return true;
        }
        if (keyCode == KeyEvent.KEYCODE_MEDIA_PLAY_PAUSE && player != null) {
            if (player.isPlaying()) player.pause(); else player.play();
            return true;
        }
        return super.onKeyDown(keyCode, event);
    }

    @Override protected void onPause() { saveProgress(); super.onPause(); }
    @Override protected void onStop() { saveProgress(); super.onStop(); releasePlayer(); }

    private void releasePlayer() {
        if (player != null) { player.release(); player = null; }
    }
}
