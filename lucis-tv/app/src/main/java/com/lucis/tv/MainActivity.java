package com.lucis.tv;

import android.app.*;
import android.os.*;
import android.graphics.Color;
import android.content.*;
import android.net.Uri;
import android.view.*;
import android.widget.*;
import java.io.*;
import java.net.*;
import java.util.*;

public class MainActivity extends Activity {
    private LinearLayout list;
    private VideoView video;
    private TextView status;
    private Button playPause;
    private String currentUrl = "";

    @Override public void onCreate(Bundle b) {
        super.onCreate(b);
        getWindow().setFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON, WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        buildUi();
    }

    private TextView text(String s, int size) {
        TextView t = new TextView(this); t.setText(s); t.setTextColor(Color.WHITE); t.setTextSize(size); t.setPadding(18,10,18,10); return t;
    }

    private Button button(String s) {
        Button b = new Button(this); b.setText(s); b.setTextSize(18); b.setFocusable(true); b.setAllCaps(false); return b;
    }

    private void buildUi() {
        LinearLayout root = new LinearLayout(this); root.setOrientation(LinearLayout.VERTICAL); root.setBackgroundColor(Color.rgb(12,12,14)); root.setPadding(26,18,26,18);
        TextView title = text("Lucis TV", 30); title.setTypeface(null, 1); root.addView(title);
        status = text("小米电视 EA55 轻量版 · 仅播放你有权访问的直播/视频源", 14); status.setTextColor(Color.LTGRAY); root.addView(status);

        LinearLayout actions = new LinearLayout(this); actions.setOrientation(LinearLayout.HORIZONTAL);
        Button importM3u = button("导入 M3U"); Button openVideo = button("打开视频链接"); playPause = button("播放 / 暂停"); Button stop = button("停止");
        actions.addView(importM3u); actions.addView(openVideo); actions.addView(playPause); actions.addView(stop); root.addView(actions);

        video = new VideoView(this); video.setBackgroundColor(Color.BLACK); video.setFocusable(true);
        root.addView(video, new LinearLayout.LayoutParams(-1, 0, 5));

        TextView channelTitle = text("频道 / 播放列表", 20); root.addView(channelTitle);
        ScrollView sc = new ScrollView(this); list = new LinearLayout(this); list.setOrientation(LinearLayout.VERTICAL); sc.addView(list); root.addView(sc, new LinearLayout.LayoutParams(-1, 0, 4));

        importM3u.setOnClickListener(v -> askPlaylist());
        openVideo.setOnClickListener(v -> askVideo());
        playPause.setOnClickListener(v -> toggle());
        stop.setOnClickListener(v -> { video.stopPlayback(); status.setText("已停止"); });

        String saved = getPreferences(MODE_PRIVATE).getString("m3u", "");
        if (!saved.isEmpty()) loadPlaylist(saved);
        setContentView(root);
    }

    private void askPlaylist() {
        EditText e = new EditText(this); e.setHint("https://example.com/list.m3u"); e.setSingleLine(true);
        new AlertDialog.Builder(this).setTitle("M3U / M3U8 播放列表网址").setView(e)
            .setPositiveButton("载入", (d,w)->{ String u=e.getText().toString().trim(); if(!u.isEmpty()){ getPreferences(MODE_PRIVATE).edit().putString("m3u",u).apply(); loadPlaylist(u);} })
            .setNegativeButton("取消", null).show();
    }

    private void askVideo() {
        EditText e = new EditText(this); e.setHint("https://.../video.m3u8 或 mp4"); e.setSingleLine(true);
        new AlertDialog.Builder(this).setTitle("直接播放视频链接").setView(e)
            .setPositiveButton("播放", (d,w)-> playUrl(e.getText().toString().trim(), "网络视频"))
            .setNegativeButton("取消", null).show();
    }

    private void loadPlaylist(String url) {
        status.setText("正在载入播放列表…");
        new Thread(() -> {
            final ArrayList<String[]> items = new ArrayList<>();
            try {
                HttpURLConnection c=(HttpURLConnection)new URL(url).openConnection(); c.setConnectTimeout(8000); c.setReadTimeout(10000); c.setRequestProperty("User-Agent","LucisTV/0.1");
                BufferedReader r=new BufferedReader(new InputStreamReader(c.getInputStream())); String line, name="频道";
                while((line=r.readLine())!=null){ line=line.trim(); if(line.startsWith("#EXTINF")){ int p=line.lastIndexOf(','); if(p>=0 && p+1<line.length()) name=line.substring(p+1).trim(); } else if(!line.isEmpty() && !line.startsWith("#")){ items.add(new String[]{name,line}); name="频道"; } }
                r.close();
                runOnUiThread(() -> showItems(items));
            } catch(Exception ex){ runOnUiThread(() -> status.setText("载入失败："+ex.getClass().getSimpleName()+" · 请检查网络或源地址")); }
        }).start();
    }

    private void showItems(ArrayList<String[]> items) {
        list.removeAllViews(); status.setText("已载入 "+items.size()+" 个频道/条目");
        if(items.isEmpty()){ list.addView(text("播放列表为空，或格式无法识别。",16)); return; }
        for(String[] it: items){ Button b=button(it[0]); b.setGravity(Gravity.LEFT|Gravity.CENTER_VERTICAL); b.setOnClickListener(v -> playUrl(it[1], it[0])); list.addView(b, new LinearLayout.LayoutParams(-1, -2)); }
    }

    private void playUrl(String url, String name) {
        if(url==null || url.isEmpty()) return; currentUrl=url; status.setText("正在播放："+name);
        try { video.setVideoURI(Uri.parse(url)); video.setMediaController(new MediaController(this)); video.requestFocus(); video.start(); }
        catch(Exception e){ status.setText("播放失败："+e.getClass().getSimpleName()); }
    }

    private void toggle(){ if(video.isPlaying()){ video.pause(); status.setText("已暂停"); } else { video.start(); status.setText(currentUrl.isEmpty()?"暂无播放地址":"继续播放"); } }

    @Override public boolean onKeyDown(int keyCode, KeyEvent event) {
        if((keyCode==KeyEvent.KEYCODE_MEDIA_PLAY_PAUSE || keyCode==KeyEvent.KEYCODE_MEDIA_PLAY || keyCode==KeyEvent.KEYCODE_MEDIA_PAUSE) && video!=null){ toggle(); return true; }
        return super.onKeyDown(keyCode,event);
    }
}
