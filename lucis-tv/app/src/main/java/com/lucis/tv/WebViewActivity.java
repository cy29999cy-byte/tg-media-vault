package com.lucis.tv;

import android.app.*;
import android.os.*;
import android.content.*;
import android.graphics.Color;
import android.net.Uri;
import android.view.*;
import android.webkit.*;
import android.widget.*;

public class WebViewActivity extends Activity {
    private WebView web;
    private LinearLayout top;
    private String startUrl;
    private String titleText;

    @Override public void onCreate(Bundle b){
        super.onCreate(b);
        startUrl=getIntent().getStringExtra("url");titleText=getIntent().getStringExtra("title");
        if(startUrl==null||!startUrl.startsWith("https://")){finish();return;}
        if(titleText==null)titleText="直播平台";
        buildUi();
        web.loadUrl(startUrl);
    }

    private Button button(String s){Button b=new Button(this);b.setText(s);b.setTextSize(15);b.setFocusable(true);b.setAllCaps(false);return b;}

    private void buildUi(){
        LinearLayout root=new LinearLayout(this);root.setOrientation(LinearLayout.VERTICAL);root.setBackgroundColor(Color.BLACK);
        top=new LinearLayout(this);top.setOrientation(LinearLayout.HORIZONTAL);top.setPadding(10,6,10,6);top.setBackgroundColor(Color.rgb(18,19,24));
        Button back=button("← 返回");Button home=button("⌂ 首页");Button reload=button("↻ 刷新");Button external=button("外部打开");
        TextView title=new TextView(this);title.setText(titleText);title.setTextColor(Color.WHITE);title.setTextSize(16);title.setGravity(Gravity.CENTER_VERTICAL);title.setPadding(16,0,16,0);
        top.addView(back);top.addView(home);top.addView(reload);top.addView(title,new LinearLayout.LayoutParams(0,-1,1f));top.addView(external);root.addView(top,new LinearLayout.LayoutParams(-1,64));

        web=new WebView(this);web.setFocusable(true);web.setFocusableInTouchMode(true);root.addView(web,new LinearLayout.LayoutParams(-1,0,1f));
        WebSettings s=web.getSettings();s.setJavaScriptEnabled(true);s.setDomStorageEnabled(true);s.setDatabaseEnabled(true);s.setMediaPlaybackRequiresUserGesture(false);s.setLoadWithOverviewMode(true);s.setUseWideViewPort(true);s.setBuiltInZoomControls(false);s.setDisplayZoomControls(false);s.setCacheMode(WebSettings.LOAD_DEFAULT);s.setUserAgentString(s.getUserAgentString()+" LucisTV/2.0 AndroidTV");
        if(Build.VERSION.SDK_INT>=21)s.setMixedContentMode(WebSettings.MIXED_CONTENT_COMPATIBILITY_MODE);

        web.setWebChromeClient(new WebChromeClient(){
            @Override public void onProgressChanged(WebView view,int progress){setTitle(titleText+" · "+progress+"%");}
        });
        web.setWebViewClient(new WebViewClient(){
            @Override public boolean shouldOverrideUrlLoading(WebView view,WebResourceRequest req){
                Uri u=req.getUrl();String scheme=u.getScheme();
                if("http".equalsIgnoreCase(scheme)||"https".equalsIgnoreCase(scheme))return false;
                try{startActivity(new Intent(Intent.ACTION_VIEW,u));}catch(Exception ignored){}
                return true;
            }
            @Override public void onReceivedError(WebView view,WebResourceRequest req,WebResourceError err){
                if(req.isForMainFrame())Toast.makeText(WebViewActivity.this,"页面加载失败，可尝试刷新或外部打开",Toast.LENGTH_LONG).show();
            }
        });

        back.setOnClickListener(v->{if(web.canGoBack())web.goBack();else finish();});
        home.setOnClickListener(v->web.loadUrl(startUrl));
        reload.setOnClickListener(v->web.reload());
        external.setOnClickListener(v->{try{startActivity(new Intent(Intent.ACTION_VIEW,Uri.parse(web.getUrl()==null?startUrl:web.getUrl())));}catch(Exception e){Toast.makeText(this,"没有可用的外部浏览器/官方应用",Toast.LENGTH_SHORT).show();}});
        setContentView(root);web.requestFocus();
    }

    @Override public boolean onKeyDown(int keyCode,KeyEvent event){
        if(keyCode==KeyEvent.KEYCODE_BACK){if(web!=null&&web.canGoBack()){web.goBack();return true;}}
        if(keyCode==KeyEvent.KEYCODE_MENU){top.setVisibility(top.getVisibility()==View.VISIBLE?View.GONE:View.VISIBLE);return true;}
        return super.onKeyDown(keyCode,event);
    }

    @Override protected void onDestroy(){if(web!=null){web.stopLoading();web.destroy();web=null;}super.onDestroy();}
}
