package tr.olcumkarti.mobil;

import android.os.Bundle;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebView;

import androidx.webkit.WebViewCompat;
import androidx.webkit.WebViewFeature;

import com.getcapacitor.BridgeActivity;
import com.getcapacitor.BridgeWebViewClient;

import java.io.ByteArrayInputStream;
import java.net.CookieHandler;
import java.util.Collections;
import java.util.HashMap;

import tr.olcumkarti.mobil.ag.KartAgPlugin;
import tr.olcumkarti.mobil.kasa.KasaPlugin;
import tr.olcumkarti.mobil.kesif.KesifPlugin;

public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(KartAgPlugin.class);
        registerPlugin(KesifPlugin.class);
        registerPlugin(KasaPlugin.class);
        super.onCreate(savedInstanceState);

        // Capacitor butun HttpURLConnection'lara bir cerez yoneticisi takar (ve adresi gunluge yazar).
        // Kart cerez kullanmaz: kart baglantilari cerez tasimasin, saklamasin.
        CookieHandler.setDefault(null);

        // WebRTC: CSP ve istek kapisi kapsamaz (olculdu) -> arayuzler belge basinda kaldirilir.
        if (WebViewFeature.isFeatureSupported(WebViewFeature.DOCUMENT_START_SCRIPT)) {
            WebViewCompat.addDocumentStartJavaScript(bridge.getWebView(), WebKapi.INSTANCE.getRTC_KAPAT(), Collections.singleton("*"));
        }

        // Aga cikan TEK yol KartAg (WebKapi): WebView paket disi hicbir adrese istek yapamaz, gezinemez;
        // dis adres tarayiciya da ACTIRILMAZ.
        bridge.setWebViewClient(new BridgeWebViewClient(bridge) {
            @Override
            public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
                if (!WebKapi.INSTANCE.izinli(request.getUrl().toString())) {
                    return new WebResourceResponse("text/plain", "utf-8", 403, "Engellendi",
                            new HashMap<>(), new ByteArrayInputStream(new byte[0]));
                }
                return super.shouldInterceptRequest(view, request);
            }

            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                if (!WebKapi.INSTANCE.izinli(request.getUrl().toString())) return true;
                return super.shouldOverrideUrlLoading(view, request);
            }
        });
    }
}
