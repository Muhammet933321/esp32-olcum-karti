package tr.olcumkarti.mobil;

import android.os.Bundle;

import com.getcapacitor.BridgeActivity;

import tr.olcumkarti.mobil.ag.KartAgPlugin;

public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(KartAgPlugin.class);
        super.onCreate(savedInstanceState);
    }
}
