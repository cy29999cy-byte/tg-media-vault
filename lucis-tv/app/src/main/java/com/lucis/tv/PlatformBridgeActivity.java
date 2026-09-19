package com.lucis.tv;

import android.app.*;
import android.os.*;
import android.content.*;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.net.Uri;
import android.view.*;
import android.widget.*;
import java.util.*;

public class PlatformBridgeActivity extends Activity {
    private TextView status;
    private LinearLayout body;

    static class AppTarget{
        String name; String[] packages; String fallback; String hint;
        AppTarget(String n,String[] p,String f,String h){name=n;packages=p;fallback=f;hint=h;}
    }

    private final AppTarget[] targets=new AppTarget[]{
        new AppTarget("虎牙 TV / 云视听虎电竞",
                new String[]{"com.huya.nftv"},
                "https://www.huya.com/g/2135",
                "进入虎牙后搜索：一起看 / 港片 / 星爷 / 英叔 / 成龙"),
        new AppTarget("斗鱼 TV",
                new String[]{"air.tv.douyu.android"},
                "https://www.douyu.com/playlist/all",
                "进入斗鱼后搜索：粤语电影 / 一起看电影 / 经典影片 / 林正英 / 周星驰")
    };

    @Override public void onCreate(Bundle b){
        super.onCreate(b);
        buildUi();
    }

    private TextView text(String s,int size){
        TextView t=new TextView(this);t.setText(s);t.setTextColor(Color.WHITE);t.setTextSize(size);t.setPadding(14,8,14,8);return t;
    }

    private Button button(String s){
        Button b=new Button(this);b.setText(s);b.setTextSize(17);b.setFocusable(true);b.setAllCaps(false);b.setMinHeight(64);return b;
    }

    private void buildUi(){
        LinearLayout root=new LinearLayout(this);root.setOrientation(LinearLayout.VERTICAL);root.setBackgroundColor(Color.rgb(7,8,12));root.setPadding(44,34,44,34);
        TextView title=text("经典港片直播 · 平台客户端",30);title.setTypeface(null,1);root.addView(title);
        status=text("优先启动电视里已安装的官方客户端，避开电视 WebView 播放兼容问题。",15);status.setTextColor(Color.LTGRAY);root.addView(status);

        body=new LinearLayout(this);body.setOrientation(LinearLayout.VERTICAL);root.addView(body,new LinearLayout.LayoutParams(-1,0,1f));

        for(AppTarget t:targets)addTarget(t);

        Button fallback=button("🌐 备用：平台网页版入口");
        fallback.setOnClickListener(v->{Intent i=new Intent(this,PortalActivity.class);i.putExtra("filter","港片");startActivity(i);});
        body.addView(fallback);

        TextView note=text("提示：平台内具体电影和直播房会实时变化。Lucis TV 只负责把电视端入口集中起来；客户端本身的登录、清晰度和节目安排由平台决定。",13);
        note.setTextColor(Color.rgb(145,148,158));body.addView(note);

        setContentView(root);
        if(body.getChildCount()>0)body.getChildAt(0).requestFocus();
    }

    private void addTarget(AppTarget t){
        LinearLayout card=new LinearLayout(this);card.setOrientation(LinearLayout.VERTICAL);card.setPadding(0,8,0,12);
        boolean installed=findInstalledPackage(t)!=null;
        Button launch=button((installed?"▶ ":"＋ ")+t.name+(installed?" · 已安装":" · 未检测到"));
        launch.setOnClickListener(v->launchTarget(t));
        card.addView(launch);
        TextView hint=text(t.hint,13);hint.setTextColor(Color.rgb(180,182,190));card.addView(hint);
        body.addView(card);
    }

    private String findInstalledPackage(AppTarget t){
        PackageManager pm=getPackageManager();
        for(String pkg:t.packages){
            try{pm.getPackageInfo(pkg,0);return pkg;}catch(Exception ignored){}
        }
        return null;
    }

    private void launchTarget(AppTarget t){
        String pkg=findInstalledPackage(t);
        if(pkg!=null){
            Intent launch=getPackageManager().getLaunchIntentForPackage(pkg);
            if(launch!=null){launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);startActivity(launch);status.setText("已启动 "+t.name+"。返回键可回 Lucis TV。");return;}
        }
        new AlertDialog.Builder(this)
                .setTitle(t.name+" 未安装")
                .setMessage("电视里暂时没有检测到这个客户端。你可以先用平台备用入口；安装 TV 客户端后，Lucis TV 会自动优先直接启动它。\n\n"+t.hint)
                .setPositiveButton("打开备用入口",(d,w)->{
                    Intent i=new Intent(this,WebViewActivity.class);i.putExtra("url",t.fallback);i.putExtra("title",t.name);startActivity(i);
                })
                .setNegativeButton("取消",null).show();
    }
}
