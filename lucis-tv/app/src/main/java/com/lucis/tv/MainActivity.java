package com.lucis.tv;

import android.app.*;
import android.os.*;
import android.graphics.Color;
import android.content.*;
import android.view.*;
import android.widget.*;
import java.io.*;
import java.net.*;
import java.util.*;

public class MainActivity extends Activity {
    private LinearLayout list;
    private TextView status;
    private final ArrayList<String[]> items = new ArrayList<>();

    @Override public void onCreate(Bundle b) {
        super.onCreate(b);
        getWindow().setFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON, WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        buildUi();
    }

    private TextView text(String s, int size) {
        TextView t = new TextView(this);
        t.setText(s);
        t.setTextColor(Color.WHITE);
        t.setTextSize(size);
        t.setPadding(18,10,18,10);
        return t;
    }

    private Button button(String s) {
        Button b = new Button(this);
        b.setText(s);
        b.setTextSize(18);
        b.setFocusable(true);
        b.setAllCaps(false);
        return b;
    }

    private void buildUi() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.HORIZONTAL);
        root.setBackgroundColor(Color.rgb(9,10,13));
        root.setPadding(34,24,34,24);

        LinearLayout left = new LinearLayout(this);
        left.setOrientation(LinearLayout.VERTICAL);
        LinearLayout.LayoutParams leftLp = new LinearLayout.LayoutParams(0, -1, 4f);
        leftLp.setMargins(0,0,26,0);
        root.addView(left, leftLp);

        TextView title = text("LUCIS TV", 32);
        title.setTypeface(null, 1);
        left.addView(title);

        TextView subtitle = text("小米电视 EA55 · v0.2", 15);
        subtitle.setTextColor(Color.LTGRAY);
        left.addView(subtitle);

        status = text("添加你有权使用的 M3U/M3U8 播放列表或视频地址。", 14);
        status.setTextColor(Color.rgb(180,180,188));
        left.addView(status);

        Button importM3u = button("导入 M3U 播放列表");
        Button openVideo = button("直接播放视频链接");
        Button clear = button("清空已保存播放列表");
        left.addView(importM3u);
        left.addView(openVideo);
        left.addView(clear);

        TextView note = text("Lucis TV 本身不内置盗版片源、不绕过付费或 DRM。你可以添加公开合法频道、自己的 NAS/Jellyfin 转码地址或已授权 IPTV 源。", 13);
        note.setTextColor(Color.rgb(130,134,145));
        left.addView(note);

        LinearLayout right = new LinearLayout(this);
        right.setOrientation(LinearLayout.VERTICAL);
        root.addView(right, new LinearLayout.LayoutParams(0, -1, 6f));

        TextView channelTitle = text("频道", 23);
        channelTitle.setTypeface(null, 1);
        right.addView(channelTitle);

        ScrollView sc = new ScrollView(this);
        list = new LinearLayout(this);
        list.setOrientation(LinearLayout.VERTICAL);
        sc.addView(list);
        right.addView(sc, new LinearLayout.LayoutParams(-1, 0, 1f));
        showEmpty();

        importM3u.setOnClickListener(v -> askPlaylist());
        openVideo.setOnClickListener(v -> askVideo());
        clear.setOnClickListener(v -> {
            getSharedPreferences("lucis", MODE_PRIVATE).edit().remove("m3u").apply();
            items.clear();
            showEmpty();
            status.setText("已清空播放列表");
        });

        setContentView(root);

        String saved = getSharedPreferences("lucis", MODE_PRIVATE).getString("m3u", "");
        if (!saved.isEmpty()) loadPlaylist(saved);
    }

    private void askPlaylist() {
        EditText e = new EditText(this);
        e.setHint("https://example.com/list.m3u");
        e.setSingleLine(true);
        new AlertDialog.Builder(this)
            .setTitle("M3U / M3U8 播放列表网址")
            .setView(e)
            .setPositiveButton("载入", (d,w) -> {
                String u = e.getText().toString().trim();
                if (!u.isEmpty()) {
                    getSharedPreferences("lucis", MODE_PRIVATE).edit().putString("m3u",u).apply();
                    loadPlaylist(u);
                }
            })
            .setNegativeButton("取消", null)
            .show();
    }

    private void askVideo() {
        EditText e = new EditText(this);
        e.setHint("https://.../video.m3u8 或 mp4");
        e.setSingleLine(true);
        new AlertDialog.Builder(this)
            .setTitle("直接播放视频链接")
            .setView(e)
            .setPositiveButton("播放", (d,w) -> playUrl(e.getText().toString().trim(), "网络视频"))
            .setNegativeButton("取消", null)
            .show();
    }

    private void loadPlaylist(String url) {
        status.setText("正在载入播放列表…");
        new Thread(() -> {
            ArrayList<String[]> loaded = new ArrayList<>();
            try {
                HttpURLConnection c = (HttpURLConnection)new URL(url).openConnection();
                c.setConnectTimeout(8000);
                c.setReadTimeout(12000);
                c.setRequestProperty("User-Agent","LucisTV/0.2");
                int code = c.getResponseCode();
                if (code < 200 || code >= 300) throw new IOException("HTTP " + code);
                BufferedReader r = new BufferedReader(new InputStreamReader(c.getInputStream()));
                String line, name = "频道";
                while ((line = r.readLine()) != null) {
                    line = line.trim();
                    if (line.startsWith("#EXTINF")) {
                        int p = line.lastIndexOf(',');
                        if (p >= 0 && p + 1 < line.length()) name = line.substring(p + 1).trim();
                    } else if (!line.isEmpty() && !line.startsWith("#")) {
                        loaded.add(new String[]{name, line});
                        name = "频道";
                    }
                    if (loaded.size() >= 800) break;
                }
                r.close();
                runOnUiThread(() -> showItems(loaded));
            } catch(Exception ex) {
                runOnUiThread(() -> status.setText("载入失败：" + ex.getMessage()));
            }
        }).start();
    }

    private void showItems(ArrayList<String[]> loaded) {
        items.clear();
        items.addAll(loaded);
        list.removeAllViews();
        status.setText("已载入 " + items.size() + " 个频道/条目");
        if (items.isEmpty()) {
            showEmpty();
            return;
        }
        for (String[] it : items) {
            Button b = button(it[0]);
            b.setGravity(Gravity.LEFT | Gravity.CENTER_VERTICAL);
            b.setOnClickListener(v -> playUrl(it[1], it[0]));
            list.addView(b, new LinearLayout.LayoutParams(-1, -2));
        }
        if (list.getChildCount() > 0) list.getChildAt(0).requestFocus();
    }

    private void showEmpty() {
        list.removeAllViews();
        TextView t = text("暂无频道\n\n请在左侧导入你自己的 M3U 播放列表。", 16);
        t.setTextColor(Color.rgb(130,134,145));
        list.addView(t);
    }

    private void playUrl(String url, String name) {
        if (url == null || url.isEmpty()) return;
        Intent i = new Intent(this, PlayerActivity.class);
        i.putExtra("url", url);
        i.putExtra("name", name);
        startActivity(i);
    }
}
