package tr.olcumkarti.mobil.bildirim

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.ByteArrayOutputStream
import java.io.IOException
import java.io.InputStream
import java.io.OutputStream
import java.net.SocketTimeoutException

/**
 * 5E-2: MQTT abonesi, SAHTE araciyla ve SANAL saatle (gercek bekleme yok). Araci = istemcinin
 * yazdigi her pakete betikle yanit veren bellek ici baglanti.
 */
class MqttIstemciTest {
    private val KONU = "ok/a1b2c3d4e5f60718293a4b5c6d7e8f90/durum"

    private fun hex(s: String): ByteArray = ByteArray(s.length / 2) { s.substring(2 * it, 2 * it + 2).toInt(16).toByte() }
    private val CONNACK = hex("20020000")
    private val SUBACK = hex("9003000101")
    private val PINGRESP = hex("d000")
    private fun yayin(konu: String, yuk: ByteArray, qos: Int = 0, no: Int = 0, kalici: Boolean = false): ByteArray {
        val govde = MqttPaket.dize(konu) + (if (qos > 0) byteArrayOf((no shr 8).toByte(), no.toByte()) else ByteArray(0)) + yuk
        return MqttPaket.paket((3 shl 4) or (qos shl 1) or (if (kalici) 1 else 0), govde)
    }

    private fun normal(a: SahteAraci, ilk: Int): ByteArray? = when (ilk shr 4) {
        MqttPaket.CONNECT -> CONNACK
        MqttPaket.SUBSCRIBE -> SUBACK
        MqttPaket.PINGREQ -> PINGRESP
        else -> null
    }

    private fun calis(a: SahteAraci, baglandi: () -> Unit = {}, istemciAl: (MqttIstemci) -> Unit = {}, mesaj: (Yayin) -> Unit = {}): MqttBitis {
        val i = MqttIstemci(a) { a.ms }
        istemciAl(i)
        return i.calis("okm-1", "kullanici", "sinama", "ok/a1b2c3d4e5f60718293a4b5c6d7e8f90/#", baglandi, mesaj)
    }

    @Test
    fun elSikisma_connectSonraSubscribe_baytlarVektorleGibi_sonraBaglandi() {
        var baglandi = 0
        var istemci: MqttIstemci? = null
        val a = SahteAraci { arac, ilk, _ -> normal(arac, ilk) }
        a.zamanAsiminda = { istemci!!.durdur() }                 // ilk bos okumada durdur
        val b = calis(a, { baglandi++ }, { istemci = it })
        assertEquals("durduruldu", b.tur)
        assertEquals(1, baglandi)
        assertEquals(listOf(MqttPaket.CONNECT, MqttPaket.SUBSCRIBE, MqttPaket.DISCONNECT), a.turler())
        // CONNECT: temiz oturum + kullanici + parola bayraklari, keepalive 5 s.
        assertArrayEquals(MqttPaket.connect("okm-1", "kullanici", "sinama", 5), MqttPaket.paket(a.gelen[0].first, a.gelen[0].second))
        assertArrayEquals(MqttPaket.subscribe(1, "ok/a1b2c3d4e5f60718293a4b5c6d7e8f90/#", 1), MqttPaket.paket(a.gelen[1].first, a.gelen[1].second))
        assertTrue(a.kapandi)
        assertEquals(5, MqttIstemci.KEEPALIVE_S)
        assertEquals(7500L, MqttIstemci.SESSIZLIK_MS)
    }

    @Test
    fun yalnizAboneOlur_hicPublishGondermez() {
        var istemci: MqttIstemci? = null
        var tur = 0
        val a = SahteAraci { arac, ilk, _ -> normal(arac, ilk) }
        a.zamanAsiminda = { if (++tur > 60) istemci!!.durdur() }       // 30 s sanal sure
        calis(a, istemciAl = { istemci = it })
        assertFalse(a.turler().contains(MqttPaket.PUBLISH))
        assertTrue(a.turler().all { it in setOf(MqttPaket.CONNECT, MqttPaket.SUBSCRIBE, MqttPaket.PINGREQ, MqttPaket.DISCONNECT) })
    }

    @Test
    fun qos1Yayin_oncePuback_sonraMesaj_qos0PubackYok_kaliciBayrakTasinir() {
        val olay = ArrayList<String>()
        var istemci: MqttIstemci? = null
        val a = SahteAraci { arac, ilk, govde ->
            when (ilk shr 4) {
                MqttPaket.SUBSCRIBE -> SUBACK + yayin(KONU, byteArrayOf(1, 2, 3), 1, 7, true) + yayin(KONU, byteArrayOf(9), 0)
                MqttPaket.PUBACK -> { olay.add("puback:" + ((govde[0].toInt() and 0xff) shl 8 or (govde[1].toInt() and 0xff))); null }
                else -> normal(arac, ilk)
            }
        }
        a.zamanAsiminda = { istemci!!.durdur() }
        val b = calis(a, { olay.add("baglandi") }, { istemci = it }) { y -> olay.add("mesaj:${y.konu.takeLast(5)}:${y.yuk.size}:${y.qos}:${y.kalici}") }
        assertEquals("durduruldu", b.tur)
        assertEquals(listOf("baglandi", "puback:7", "mesaj:durum:3:1:true", "mesaj:durum:1:0:false"), olay)
    }

    @Test
    fun subacktanOnceGelenKaliciMesajKaybolmaz() {
        val mesajlar = ArrayList<Int>()
        var istemci: MqttIstemci? = null
        val a = SahteAraci { arac, ilk, _ ->
            if (ilk shr 4 == MqttPaket.SUBSCRIBE) yayin(KONU, byteArrayOf(5, 5), 0, 0, true) + SUBACK else normal(arac, ilk)
        }
        a.zamanAsiminda = { istemci!!.durdur() }
        calis(a, istemciAl = { istemci = it }) { mesajlar.add(it.yuk.size) }
        assertEquals(listOf(2), mesajlar)
    }

    @Test
    fun connackReddi_kodDoner_aboneOlunmaz() {
        for (kod in listOf(1, 2, 3, 4, 5)) {
            val a = SahteAraci { _, ilk, _ -> if (ilk shr 4 == MqttPaket.CONNECT) byteArrayOf(0x20, 2, 0, kod.toByte()) else null }
            val b = calis(a)
            assertEquals("ret", b.tur)
            assertEquals(kod, b.kod)
            assertEquals(listOf(MqttPaket.CONNECT), a.turler())
            assertTrue(a.kapandi)
        }
    }

    @Test
    fun aboneReddi_veBicimHatalari() {
        val ret = SahteAraci { arac, ilk, _ -> if (ilk shr 4 == MqttPaket.SUBSCRIBE) hex("9003000180") else normal(arac, ilk) }
        assertEquals("abone-ret", calis(ret).tur)
        val yanlisNo = SahteAraci { arac, ilk, _ -> if (ilk shr 4 == MqttPaket.SUBSCRIBE) hex("9003000201") else normal(arac, ilk) }
        assertEquals("bicim", calis(yanlisNo).tur)
        val connackYerine = SahteAraci { _, ilk, _ -> if (ilk shr 4 == MqttPaket.CONNECT) PINGRESP else null }
        assertEquals("bicim", calis(connackYerine).tur)
        val qos2 = SahteAraci { arac, ilk, _ -> if (ilk shr 4 == MqttPaket.SUBSCRIBE) SUBACK + yayin(KONU, byteArrayOf(1), 2, 3) else normal(arac, ilk) }
        var mesaj = 0
        assertEquals("bicim", calis(qos2) { mesaj++ }.tur)
        assertEquals(0, mesaj)
        val bozuk = SahteAraci { arac, ilk, _ -> if (ilk shr 4 == MqttPaket.SUBSCRIBE) SUBACK + hex("30ffffffff01") else normal(arac, ilk) }
        assertEquals("bicim", calis(bozuk).tur)
        val dev = SahteAraci { arac, ilk, _ -> if (ilk shr 4 == MqttPaket.SUBSCRIBE) SUBACK + hex("30") + MqttPaket.uzunlukKodla(MqttPaket.PAKET_AZAMI + 1) else normal(arac, ilk) }
        assertEquals("bicim", calis(dev).tur)
    }

    @Test
    fun elSikismaZamanAsimi_connackGelmezse10Saniye() {
        val a = SahteAraci { _, _, _ -> null }
        val t0 = a.ms
        val b = calis(a)
        assertEquals("zaman-asimi", b.tur)
        assertTrue(a.ms - t0 in 10_000L..11_000L)
        val subackYok = SahteAraci { _, ilk, _ -> if (ilk shr 4 == MqttPaket.CONNECT) CONNACK else null }
        assertEquals("zaman-asimi", calis(subackYok).tur)
    }

    @Test
    fun keepalive_5SaniyeSessizlikteBirPingreq_yanitGelinceSurer() {
        var istemci: MqttIstemci? = null
        val a = SahteAraci { arac, ilk, _ -> normal(arac, ilk) }
        val t0 = a.ms
        a.zamanAsiminda = { if (it.ms - t0 >= 26_000) istemci!!.durdur() }
        val b = calis(a, istemciAl = { istemci = it })
        assertEquals("durduruldu", b.tur)
        // 26 s'de 5 PINGREQ (5, 10, 15, 20, 25. saniyeler); hicbiri erken degil.
        assertEquals(5, a.turler().count { it == MqttPaket.PINGREQ })
    }

    @Test
    fun pingYanitsizKalirsa_7buCukSaniyedeSessiz_kartAlarmiDegil() {
        val a = SahteAraci { arac, ilk, _ -> if (ilk shr 4 == MqttPaket.PINGREQ) null else normal(arac, ilk) }
        val t0 = a.ms
        val b = calis(a)
        assertEquals("sessiz", b.tur)
        // 5 s sonra PINGREQ, ondan 7.5 s sonra vazgecilir: toplam ~12.5 s (500 ms'lik adimlarla).
        assertTrue("${a.ms - t0}", a.ms - t0 in 12_500L..13_500L)
        assertEquals(1, a.turler().count { it == MqttPaket.PINGREQ })
        assertTrue(a.kapandi)
    }

    @Test
    fun aracidanHerhangiBirPaketCanlilikSayilir_pingBeklemesiSifirlanir() {
        // PINGRESP gelmiyor ama araci her 3 s'de bir yayin yolluyor: "sessiz" DENMEZ.
        var istemci: MqttIstemci? = null
        val a = SahteAraci { arac, ilk, _ -> if (ilk shr 4 == MqttPaket.PINGREQ) null else normal(arac, ilk) }
        val t0 = a.ms
        var sonYayin = t0
        a.zamanAsiminda = {
            if (it.ms - sonYayin >= 3000) { it.kuyruk.addLast(yayin(KONU, byteArrayOf(1))); sonYayin = it.ms }
            if (it.ms - t0 >= 40_000) istemci!!.durdur()
        }
        var mesaj = 0
        val b = calis(a, istemciAl = { istemci = it }) { mesaj++ }
        assertEquals("durduruldu", b.tur)
        assertTrue(mesaj >= 12)
    }

    @Test
    fun baglantiKoparsa_koptu_hataMetniSirTasimaz() {
        val bitti = SahteAraci { arac, ilk, _ -> normal(arac, ilk) }
        bitti.zamanAsiminda = { it.akisBitti = true }
        assertEquals("koptu", calis(bitti).tur)
        val hata = SahteAraci { arac, ilk, _ -> normal(arac, ilk) }
        hata.zamanAsiminda = { it.okumaHatasi = true }
        val b = calis(hata)
        assertEquals("koptu", b.tur)
        assertEquals(0, b.kod)
        assertTrue(hata.kapandi)
        // Bitis nesnesinde yalniz sabit tur adi ve sayisal kod var (alan sayisi sabit: adres / konu tasiyacak yer yok).
        assertEquals(setOf("tur", "kod"), MqttBitis::class.java.declaredFields.map { it.name }.toSet())
    }

    @Test
    fun mesajIsleyicisiAtarsaOturumCokmez_istisnaDisariCikmaz() {
        var istemci: MqttIstemci? = null
        var n = 0
        val a = SahteAraci { arac, ilk, _ -> if (ilk shr 4 == MqttPaket.SUBSCRIBE) SUBACK + yayin(KONU, byteArrayOf(1)) + yayin(KONU, byteArrayOf(2)) else normal(arac, ilk) }
        a.zamanAsiminda = { istemci!!.durdur() }
        val b = calis(a, istemciAl = { istemci = it }) { n++; throw IllegalStateException("isleyici") }
        assertEquals("durduruldu", b.tur)
        assertEquals(2, n)
    }
}
