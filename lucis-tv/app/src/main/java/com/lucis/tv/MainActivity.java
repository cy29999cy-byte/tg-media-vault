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
    private EditText search;
    private final ArrayList<Channel> items = new ArrayList<>();
    private final ArrayList<Channel> visible = new ArrayList<>();
    private String mode = "all";

    static class Channel {
        String name;
        String url;
        String group;
        Channel(String name, String url, String group) {
            this.name = name == null || name.isEmpty() ? "频道" : name;
            this.url = url == null ? "" : url;
            this.group = group == null || group.isEmpty() ? "未分类" : group;
        }
    }

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

        TextView subtitle = text("小米电视 EA55 · v0.3", 15);
        subtitle.setTextColor(Color.LTGRAY);
        left.addView(subtitle);

        status = text("导入你有权使用的 M3U/M3U8 播放列表。", 14);
        status.setTextColor(Color.rgb(180,180,188));
        left.addView(status);

        Button all = button("全部频道");
        Button fav = button("★ 我的收藏");
        Button history = button("最近观看");
        Button importM3u = button("导入 M3U 播放列表");
        Button openVideo = button("直接播放视频链接");
        Button clear = button("清空播放列表");
        left.addView(all);
        left.addView(fav);
        left.addView(history);
        left.addView(importM3u);
        left.addView(openVideo);
        left.addView(clear);

        TextView note = text("支持频道分组、收藏、历史记录和 HLS 播放。Lucis TV 不内置盗版片源，也不绕过付费或 DRM。", 13);
        note.setTextColor(Color.rgb(130,134,145));
        left.addView(note);

        LinearLayout right = new LinearLayout(this);
        right.setOrientation(LinearLayout.VERTICAL);
        root.addView(right, new LinearLayout.LayoutParams(0, -1, 6f));

        TextView channelTitle = text("频道", 23);
        channelTitle.setTypeface(null, 1);
        right.addView(channelTitle);

        search = new EditText(this);
        search.setHint("搜索频道名称 / 分组");
        search.setSingleLine(true);
        search.setTextColor(Color.WHITE);
        search.setHintTextColor(Color.GRAY);
        search.setTextSize(17);
        search.setFocusable(true);
        right.addView(search, new LinearLayout.LayoutParams(-1, -2));

        Button doSearch = button("搜索");
        right.addView(doSearch);

        ScrollView sc = new ScrollView(this);
        list = new LinearLayout(this);
        list.setOrientation(LinearLayout.VERTICAL);
        sc.addView(list);
        right.addView(sc, new LinearLayout.LayoutParams(-1, 0, 1f));
        showEmpty("暂无频道\n\n请在左侧导入你自己的 M3U 播放列表。");

        all.setOnClickListener(v -> { mode = "all"; render(); });
        fav.setOnClickListener(v -> { mode = "fav"; render(); });
        history.setOnClickListener(v -> { mode = "history"; render(); });
        doSearch.setOnClickListener(v -> render());
        importM3u.setOnClickListener(v -> askPlaylist());
        openVideo.setOnClickListener(v -> askVideo());
        clear.setOnClickListener(v -> {
            getSharedPreferences("lucis", MODE_PRIVATE).edit().remove("m3u").apply();
            items.clear();
            visible.clear();
            showEmpty("播放列表已清空。\n\n收藏和最近观看记录仍然保留。");
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
                    mode = "all";
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

    private static String attr(String line, String key) {
        String token = key + "=\"";
        int p = line.indexOf(token);
        if (p < 0) return "";
        int s = p + token.length();
        int e = line.indexOf('"', s);
        return e > s ? line.substring(s, e).trim() : "";
    }

    private void loadPlaylist(String url) {
        status.setText("正在载入播放列表…");
        new Thread(() -> {
            ArrayList<Channel> loaded = new ArrayList<>();
            try {
                HttpURLConnection c = (HttpURLConnection)new URL(url).openConnection();
                c.setConnectTimeout(8000);
                c.setReadTimeout(12000);
                c.setRequestProperty("User-Agent","LucisTV/0.3");
                int code = c.getResponseCode();
                if (code < 200 || code >= 300) throw new IOException("HTTP " + code);
                BufferedReader r = new BufferedReader(new InputStreamReader(c.getInputStream()));
                String line, name = "频道", group = "未分类";
                while ((line = r.readLine()) != null) {
                    line = line.trim();
                    if (line.startsWith("#EXTINF")) {
                        int p = line.lastIndexOf(',');
                        if (p >= 0 && p + 1 < line.length()) name = line.substring(p + 1).trim();
                        String g = attr(line, "group-title");
                        if (!g.isEmpty()) group = g;
                    } else if (!line.isEmpty() && !line.startsWith("#")) {
                        loaded.add(new Channel(name, line, group));
                        name = "频道";
                        group = "未分类";
                    }
                    if (loaded.size() >= 1200) break;
                }
                r.close();
                runOnUiThread(() -> {
                    items.clear();
                    items.addAll(loaded);
                    status.setText("已载入 " + items.size() + " 个频道/条目");
                    render();
                });
            } catch(Exception ex) {
                runOnUiThread(() -> status.setText("载入失败：" + ex.getMessage()));
            }
        }).start();
    }

    private Set<String> favorites() {
        return new HashSet<>(getSharedPreferences("lucis", MODE_PRIVATE).getStringSet("favorites", Collections.emptySet()));
    }

    private void toggleFavorite(Channel c) {
        Set<String> set = favorites();
        if (set.contains(c.url)) set.remove(c.url); else set.add(c.url);
        getSharedPreferences("lucis", MODE_PRIVATE).edit().putStringSet("favorites", set).apply();
        render();
    }

    private ArrayList<Channel> historyItems() {
        ArrayList<Channel> out = new ArrayList<>();
        String raw = getSharedPreferences("lucis", MODE_PRIVATE).getString("history", "");
        if (raw.isEmpty()) return out;
        for (String line : raw.split("\\n")) {
            String[] p = line.split("\\t", 3);
            if (p.length >= 2) out.add(new Channel(p[1], p[0], p.length >= 3 ? p[2] : "最近观看"));
        }
        return out;
    }

    private void saveHistory(String url, String name, String group) {
        ArrayList<Channel> h = historyItems();
        h.removeIf(c -> c.url.equals(url));
        h.add(0, new Channel(name, url, group));
        StringBuilder sb = new StringBuilder();
        int max = Math.min(40, h.size());
        for (int i=0; i<max; i++) {
            Channel c = h.get(i);
            String n = c.name.replace('\t',' ').replace('\n',' ');
            String g = c.group.replace('\t',' ').replace('\n',' ');
            sb.append(c.url).append('\t').append(n).append('\t').append(g).append('\n');
        }
        getSharedPreferences("lucis", MODE_PRIVATE).edit().putString("history", sb.toString()).apply();
    }

    private void render() {
        visible.clear();
        String q = search == null ? "" : search.getText().toString().trim().toLowerCase(Locale.ROOT);
        Set<String> favs = favorites();
        ArrayList<Channel> source = mode.equals("history") ? historyItems() : items;
        for (Channel c : source) {
            if (mode.equals("fav") && !favs.contains(c.url)) continue;
            if (!q.isEmpty() && !(c.name.toLowerCase(Locale.ROOT).contains(q) || c.group.toLowerCase(Locale.ROOT).contains(q))) continue;
            visible.add(c);
        }

        list.removeAllViews();
        String label = mode.equals("fav") ? "收藏" : mode.equals("history") ? "最近观看" : "全部频道";
        status.setText(label + " · " + visible.size() + " 个条目");
        if (visible.isEmpty()) {
            showEmpty(mode.equals("fav") ? "暂无收藏。\n\n在频道右侧按 ☆ 即可收藏。" : mode.equals("history") ? "暂无观看记录。" : "没有匹配的频道。\n\n可清空搜索词后重试。");
            return;
        }

        for (Channel c : visible) {
            LinearLayout row = new LinearLayout(this);
            row.setOrientation(LinearLayout.HORIZONTAL);

            Button play = button((c.group.equals("未分类") ? "" : "[" + c.group + "]  ") + c.name);
            play.setGravity(Gravity.LEFT | Gravity.CENTER_VERTICAL);
            play.setOnClickListener(v -> playUrl(c.url, c.name, c.group));
            row.addView(play, new LinearLayout.LayoutParams(0, -2, 1f));

            Button star = button(favs.contains(c.url) ? "★" : "☆");
            star.setContentDescription(favs.contains(c.url) ? "取消收藏" : "收藏");
            star.setOnClickListener(v -> toggleFavorite(c));
            row.addView(star, new LinearLayout.LayoutParams(90, -2));
            list.addView(row, new LinearLayout.LayoutParams(-1, -2));
        }
        if (list.getChildCount() > 0) {
            View row = list.getChildAt(0);
            if (row instanceof ViewGroup && ((ViewGroup)row).getChildCount() > 0) ((ViewGroup)row).getChildAt(0).requestFocus();
        }
    }

    private void showEmpty(String message) {
        list.removeAllViews();
        TextView t = text(message, 16);
        t.setTextColor(Color.rgb(130,134,145));
        list.addView(t);
    }

    private void playUrl(String url, String name) {
        playUrl(url, name, "直接播放");
    }

    private void playUrl(String url, String name, String group) {
        if (url == null || url.isEmpty()) return;
        saveHistory(url, name, group);
        Intent i = new Intent(this, PlayerActivity.class);
        i.putExtra("url", url);
        i.putExtra("name", name);
        startActivity(i);
    }
}
