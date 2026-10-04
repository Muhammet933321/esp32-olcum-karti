package tr.olcumkarti.mobil;

import android.os.Bundle;

import com.getcapacitor.BridgeActivity;

import tr.olcumkarti.mobil.ag.KartAgPlugin;
import tr.olcumkarti.mobil.kesif.KesifPlugin;

public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(KartAgPlugin.class);
        registerPlugin(KesifPlugin.class);
        super.onCreate(savedInstanceState);
    }
}
