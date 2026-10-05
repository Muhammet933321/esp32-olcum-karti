package tr.olcumkarti.mobil.bildirim

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.res.Configuration
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import tr.olcumkarti.mobil.MainActivity
import tr.olcumkarti.mobil.R
import java.util.Locale

/**
 * Bildirimleri EKRANA koyan ince kabuk (tasarim A38, A43). Karar ve metin saf katmanlarda
 * (BildirimKarar, BildirimMetin); burasi yalniz kanal, kimlik ve Android cagrisi.
 *  - kanallar: `izleme` (sessiz, kalici), `uyari` (sesli), `bilgi`
 *  - `Bildirim.etiket` Android bildirim ETIKETI olur: ayni etiket onceki bildirimi GUNCELLER (A33, A35)
 *  - metinler strings.xml'den, AYARDAKI dilde (telefonun dili degil) — tr varsayilan, en `values-en`
 * Bildirim izni yoksa cagrilar sessizce duser (uygulama calismaya devam eder — A37).
 */
class BildirimGosterici(ctx: Context, dil: String) {
    private val uyg: Context = ctx.applicationContext
    private val dilli: Context = uyg.createConfigurationContext(Configuration(uyg.resources.configuration).apply { setLocale(Locale(dil)) })
    private val metin = BildirimMetin(dil, ::sozluk)
    private val yonetici = NotificationManagerCompat.from(uyg)

    /** "bld.kopuk" -> R.string.bld_kopuk (yoksa null). */
    private fun sozluk(anahtar: String): String? {
        val no = dilli.resources.getIdentifier(anahtar.replace('.', '_'), "string", uyg.packageName)
        return if (no == 0) null else dilli.getString(no)
    }

    fun izinVar(): Boolean = yonetici.areNotificationsEnabled()

    fun kanallariKur() {
        val y = uyg.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        fun kanal(kimlik: String, ad: Int, onem: Int, sessiz: Boolean) {
            val k = NotificationChannel(kimlik, dilli.getString(ad), onem)
            if (sessiz) { k.setSound(null, null); k.enableVibration(false); k.setShowBadge(false) }
            y.createNotificationChannel(k)
        }
        kanal(Kanal.IZLEME, R.string.kanal_izleme, NotificationManager.IMPORTANCE_LOW, true)
        kanal(Kanal.UYARI, R.string.kanal_uyari, NotificationManager.IMPORTANCE_HIGH, false)
        kanal(Kanal.BILGI, R.string.kanal_bilgi, NotificationManager.IMPORTANCE_DEFAULT, false)
    }

    private fun uygulamayiAc(): PendingIntent =
        PendingIntent.getActivity(uyg, 0, Intent(uyg, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)

    private fun kur(kanal: String, yazi: String): NotificationCompat.Builder =
        NotificationCompat.Builder(uyg, kanal)
            .setSmallIcon(R.drawable.ic_bildirim)
            .setContentTitle(metin.baslik())
            .setContentText(yazi)
            .setStyle(NotificationCompat.BigTextStyle().bigText(yazi))
            .setContentIntent(uygulamayiAc())
            // Kilit ekraninda icerik gizli (oturum numarasi, olcum degeri gorunmez).
            .setVisibility(NotificationCompat.VISIBILITY_PRIVATE)

    /** Kart haberi. Sessiz = daha once gosterilmis bildirimin ayrintili hali (ses / titresim yok). */
    fun goster(b: Bildirim) {
        val n = kur(Kanal.sinifin(b.sinif), metin.kur(b)).setAutoCancel(true).setSilent(b.sessiz).build()
        gonder(b.etiket, KART_NO, n)
    }

    /** Servisin kalici bildirimi (`durum`: IzlemeDongusu'nun durum adi). */
    fun izleme(durum: String): Notification =
        kur(Kanal.IZLEME, dilli.getString(izlemeMetni(durum))).setOngoing(true).setSilent(true).build()

    fun izlemeGuncelle(durum: String) = gonder(null, IZLEME_NO, izleme(durum))

    /** Izleme "ayar" ile bitti: kalici degil, dokununca uygulama acilir (A31). */
    fun ayarYenile() {
        gonder(AYAR_ETIKETI, KART_NO, kur(Kanal.BILGI, dilli.getString(R.string.izleme_ayar)).setAutoCancel(true).build())
    }

    fun ayarYenileKaldir() = yonetici.cancel(AYAR_ETIKETI, KART_NO)

    private fun gonder(etiket: String?, no: Int, n: Notification) {
        try { yonetici.notify(etiket, no, n) } catch (_: SecurityException) {}      // izin yok: sessizce duser
    }

    companion object {
        const val IZLEME_NO = 1
        const val KART_NO = 2
        const val AYAR_ETIKETI = "ayar"

        fun izlemeMetni(durum: String): Int = when (durum) {
            "izleniyor" -> R.string.izleme_izleniyor
            "internet" -> R.string.izleme_internet
            "guven" -> R.string.izleme_guven
            "araci" -> R.string.izleme_araci
            else -> R.string.izleme_baglaniyor
        }
    }
}
