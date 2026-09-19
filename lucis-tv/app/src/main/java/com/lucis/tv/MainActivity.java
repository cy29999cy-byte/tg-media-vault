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
    private final ArrayList<Channel> items=new ArrayList<>();
    private final ArrayList<Channel> visible=new ArrayList<>();
    private String mode="public";

    static class Channel{
        String name,url,group; boolean builtIn;
        Channel(String n,String u,String g,boolean b){name=n==null||n.isEmpty()?"频道":n;url=u==null?"":u;group=g==null||g.isEmpty()?"未分类":g;builtIn=b;}
    }

    @Override public void onCreate(Bundle b){
        super.onCreate(b);
        getWindow().setFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON,WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        buildUi();
    }

    private TextView text(String s,int size){
        TextView t=new TextView(this);t.setText(s);t.setTextColor(Color.WHITE);t.setTextSize(size);t.setPadding(12,7,12,7);return t;
    }

    private Button button(String s){
        Button b=new Button(this);b.setText(s);b.setTextSize(16);b.setFocusable(true);b.setAllCaps(false);b.setMinHeight(58);return b;
    }

    private void seedPublicChannels(){
        items.add(new Channel("港台电视31","https://rthktv31-live.akamaized.net/hls/live/2036818/RTHKTV31/master.m3u8","香港 · 公共直播",true));
        items.add(new Channel("港台电视32","https://rthktv32-live.akamaized.net/hls/live/2036819/RTHKTV32/master.m3u8","香港 · 公共直播",true));
    }

    private void buildUi(){
        seedPublicChannels();

        LinearLayout root=new LinearLayout(this);
        root.setOrientation(LinearLayout.HORIZONTAL);
        root.setBackgroundColor(Color.rgb(6,7,11));
        root.setPadding(28,20,28,20);

        ScrollView leftScroll=new ScrollView(this);
        LinearLayout left=new LinearLayout(this);left.setOrientation(LinearLayout.VERTICAL);leftScroll.addView(left);
        LinearLayout.LayoutParams leftLp=new LinearLayout.LayoutParams(0,-1,3.6f);leftLp.setMargins(0,0,22,0);root.addView(leftScroll,leftLp);

        TextView title=text("LUCIS TV",31);title.setTypeface(null,1);left.addView(title);
        TextView subtitle=text("EA55 · 2.1 · TV 客户端桥接版",14);subtitle.setTextColor(Color.LTGRAY);left.addView(subtitle);
        status=text("优先调用虎牙/斗鱼电视客户端；网页入口只作为备用。",13);status.setTextColor(Color.rgb(184,184,194));left.addView(status);

        Button hkLive=button("🔥 经典港片直播");
        Button platforms=button("🎥 虎牙 / 斗鱼");
        Button resume=button("▶ 继续观看");
        Button classics=button("🎞 我的港片库");
        Button publicLive=button("📺 香港公开直播");
        Button fav=button("★ 我的收藏");
        Button history=button("最近观看");
        Button all=button("全部频道");
        Button importM3u=button("导入 M3U");
        Button openVideo=button("直接播放链接");
        Button update=button("⬆ 检查更新");

        left.addView(hkLive);left.addView(platforms);left.addView(resume);left.addView(classics);left.addView(publicLive);
        left.addView(fav);left.addView(history);left.addView(all);left.addView(importM3u);left.addView(openVideo);left.addView(update);

        LinearLayout right=new LinearLayout(this);right.setOrientation(LinearLayout.VERTICAL);root.addView(right,new LinearLayout.LayoutParams(0,-1,6.4f));
        TextView channelTitle=text("现在可看",22);channelTitle.setTypeface(null,1);right.addView(channelTitle);

        search=new EditText(this);search.setHint("搜索频道名称 / 分组");search.setSingleLine(true);search.setTextColor(Color.WHITE);search.setHintTextColor(Color.GRAY);search.setTextSize(16);right.addView(search);
        Button doSearch=button("搜索");right.addView(doSearch);

        ScrollView sc=new ScrollView(this);list=new LinearLayout(this);list.setOrientation(LinearLayout.VERTICAL);sc.addView(list);right.addView(sc,new LinearLayout.LayoutParams(-1,0,1f));

        hkLive.setOnClickListener(v->startActivity(new Intent(this,PlatformBridgeActivity.class)));
        platforms.setOnClickListener(v->startActivity(new Intent(this,PlatformBridgeActivity.class)));
        resume.setOnClickListener(v->resumeLast());
        classics.setOnClickListener(v->startActivity(new Intent(this,LibraryActivity.class)));
        publicLive.setOnClickListener(v->{mode="public";render();});
        fav.setOnClickListener(v->{mode="fav";render();});
        history.setOnClickListener(v->{mode="history";render();});
        all.setOnClickListener(v->{mode="all";render();});
        doSearch.setOnClickListener(v->render());
        importM3u.setOnClickListener(v->askPlaylist());
        openVideo.setOnClickListener(v->askVideo());
        update.setOnClickListener(v->startActivity(new Intent(this,UpdateActivity.class)));

        setContentView(root);
        render();

        String saved=getSharedPreferences("lucis",MODE_PRIVATE).getString("m3u","");
        if(!saved.isEmpty())loadPlaylist(saved);
    }

    private void resumeLast(){
        String u=getSharedPreferences("lucis",MODE_PRIVATE).getString("last_url","");
        String n=getSharedPreferences("lucis",MODE_PRIVATE).getString("last_name","继续观看");
        if(u.isEmpty()){Toast.makeText(this,"还没有可继续观看的影片",Toast.LENGTH_SHORT).show();return;}
        playUrl(u,n,"继续观看");
    }

    private void askPlaylist(){
        EditText e=new EditText(this);e.setHint("https://example.com/list.m3u");e.setSingleLine(true);
        new AlertDialog.Builder(this).setTitle("M3U / M3U8 播放列表网址").setView(e)
                .setPositiveButton("载入",(d,w)->{String u=e.getText().toString().trim();if(!u.isEmpty()){getSharedPreferences("lucis",MODE_PRIVATE).edit().putString("m3u",u).apply();mode="all";loadPlaylist(u);}})
                .setNegativeButton("取消",null).show();
    }

    private void askVideo(){
        EditText e=new EditText(this);e.setHint("https://.../video.m3u8 或 mp4");e.setSingleLine(true);
        new AlertDialog.Builder(this).setTitle("直接播放视频链接").setView(e)
                .setPositiveButton("播放",(d,w)->playUrl(e.getText().toString().trim(),"网络视频","直接播放"))
                .setNegativeButton("取消",null).show();
    }

    private static String attr(String line,String key){
        String token=key+"=\"";int p=line.indexOf(token);if(p<0)return"";int s=p+token.length();int e=line.indexOf('"',s);return e>s?line.substring(s,e).trim():"";
    }

    private void loadPlaylist(String url){
        status.setText("正在载入播放列表…");
        new Thread(()->{
            ArrayList<Channel> loaded=new ArrayList<>();
            try{
                HttpURLConnection c=(HttpURLConnection)new URL(url).openConnection();c.setConnectTimeout(8000);c.setReadTimeout(12000);c.setRequestProperty("User-Agent","LucisTV/2.1");
                int code=c.getResponseCode();if(code<200||code>=300)throw new IOException("HTTP "+code);
                BufferedReader r=new BufferedReader(new InputStreamReader(c.getInputStream()));
                String line,name="频道",group="未分类";
                while((line=r.readLine())!=null){
                    line=line.trim();
                    if(line.startsWith("#EXTINF")){
                        int p=line.lastIndexOf(',');if(p>=0&&p+1<line.length())name=line.substring(p+1).trim();
                        String g=attr(line,"group-title");if(!g.isEmpty())group=g;
                    }else if(!line.isEmpty()&&!line.startsWith("#")){
                        loaded.add(new Channel(name,line,group,false));name="频道";group="未分类";
                    }
                    if(loaded.size()>=1200)break;
                }
                r.close();
                runOnUiThread(()->{items.removeIf(ch->!ch.builtIn);items.addAll(loaded);status.setText("公开频道 + 你的列表，共 "+items.size()+" 个条目");render();});
            }catch(Exception ex){
                runOnUiThread(()->status.setText("载入失败："+ex.getMessage()));
            }
        }).start();
    }

    private Set<String> favorites(){return new HashSet<>(getSharedPreferences("lucis",MODE_PRIVATE).getStringSet("favorites",Collections.emptySet()));}

    private void toggleFavorite(Channel c){
        Set<String> set=favorites();if(set.contains(c.url))set.remove(c.url);else set.add(c.url);
        getSharedPreferences("lucis",MODE_PRIVATE).edit().putStringSet("favorites",set).apply();render();
    }

    private ArrayList<Channel> historyItems(){
        ArrayList<Channel> out=new ArrayList<>();String raw=getSharedPreferences("lucis",MODE_PRIVATE).getString("history","");
        if(raw.isEmpty())return out;
        for(String line:raw.split("\n")){String[] p=line.split("\t",3);if(p.length>=2)out.add(new Channel(p[1],p[0],p.length>=3?p[2]:"最近观看",false));}
        return out;
    }

    private void saveHistory(String url,String name,String group){
        ArrayList<Channel> h=historyItems();h.removeIf(c->c.url.equals(url));h.add(0,new Channel(name,url,group,false));
        StringBuilder sb=new StringBuilder();int max=Math.min(40,h.size());
        for(int i=0;i<max;i++){Channel c=h.get(i);sb.append(c.url).append('\t').append(c.name.replace('\t',' ').replace('\n',' ')).append('\t').append(c.group.replace('\t',' ').replace('\n',' ')).append('\n');}
        getSharedPreferences("lucis",MODE_PRIVATE).edit().putString("history",sb.toString()).apply();
    }

    private void render(){
        visible.clear();
        String q=search==null?"":search.getText().toString().trim().toLowerCase(Locale.ROOT);
        Set<String> favs=favorites();ArrayList<Channel> source=mode.equals("history")?historyItems():items;
        for(Channel c:source){
            if(mode.equals("public")&&!c.builtIn)continue;
            if(mode.equals("fav")&&!favs.contains(c.url))continue;
            if(!q.isEmpty()&&!(c.name.toLowerCase(Locale.ROOT).contains(q)||c.group.toLowerCase(Locale.ROOT).contains(q)))continue;
            visible.add(c);
        }

        list.removeAllViews();
        String label=mode.equals("public")?"香港公开直播":mode.equals("fav")?"收藏":mode.equals("history")?"最近观看":"全部频道";
        status.setText(label+" · "+visible.size()+" 个条目");

        if(visible.isEmpty()){
            TextView t=text("暂无可显示内容。",16);t.setTextColor(Color.GRAY);list.addView(t);return;
        }

        for(Channel c:visible){
            LinearLayout row=new LinearLayout(this);row.setOrientation(LinearLayout.HORIZONTAL);
            Button play=button("["+c.group+"]  "+c.name);play.setGravity(Gravity.LEFT|Gravity.CENTER_VERTICAL);play.setOnClickListener(v->playUrl(c.url,c.name,c.group));row.addView(play,new LinearLayout.LayoutParams(0,-2,1f));
            Button star=button(favs.contains(c.url)?"★":"☆");star.setOnClickListener(v->toggleFavorite(c));row.addView(star,new LinearLayout.LayoutParams(82,-2));list.addView(row);
        }

        if(list.getChildCount()>0){
            View row=list.getChildAt(0);
            if(row instanceof ViewGroup&&((ViewGroup)row).getChildCount()>0)((ViewGroup)row).getChildAt(0).requestFocus();
        }
    }

    private void playUrl(String url,String name,String group){
        if(url==null||url.isEmpty())return;
        saveHistory(url,name,group);
        Intent i=new Intent(this,PlayerActivity.class);i.putExtra("url",url);i.putExtra("name",name);startActivity(i);
    }
}
