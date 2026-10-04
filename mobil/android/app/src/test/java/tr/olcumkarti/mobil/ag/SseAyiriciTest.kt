package tr.olcumkarti.mobil.ag

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class SseAyiriciTest {
    private fun ayir(metin: String): List<String> = ozet(SseAyirici().besle(metin.toByteArray(Charsets.UTF_8)))

    private fun ozet(olaylar: List<SseOlay>): List<String> = olaylar.map { "${it.ad}|${it.veri}" }

    @Test
    fun dataSatiriBosSatirdaOlayOlur() {
        assertEquals(listOf("|D 1 2 3"), ayir("data: D 1 2 3\n\n"))
        assertEquals(listOf("|bir", "|iki"), ayir("data: bir\n\ndata: iki\n\n"))
    }

    @Test
    fun bosSatirGelmedenOlayCikmaz_yarimSatirSonrakiBeslemedeTamamlanir() {
        val a = SseAyirici()
        assertTrue(a.besle("data: D 1".toByteArray()).isEmpty())
        assertTrue(a.besle(" 2 3\n".toByteArray()).isEmpty())
        assertEquals(listOf("|D 1 2 3"), ozet(a.besle("\n".toByteArray())))
    }

    @Test
    fun olayAdiTasinir_sonrakiOlaydaSifirlanir() {
        assertEquals(listOf("dolu|4", "|D 1"), ayir("event: dolu\ndata: 4\n\ndata: D 1\n\n"))
        assertEquals(listOf("kimlik|{\"jeton\":\"x\"}"), ayir("event: kimlik\ndata: {\"jeton\":\"x\"}\n\n"))
    }

    @Test
    fun idRetryYorumVeBilinmeyenAlanOlayaGirmez() {
        assertEquals(listOf("|D 1"), ayir("retry: 3000\n\n: kalp\n\nid: 17\ndata: D 1\nbaska: x\nalansiz\n\n"))
        assertTrue(ayir(": kalp\n\n: kalp\n\nretry: 3000\n\nid: 5\n\n").isEmpty())
    }

    @Test
    fun verisizOlayDagitilmaz() {
        assertTrue(ayir("event: dolu\n\n").isEmpty())
        assertEquals(listOf("|x"), ayir("event: bos\n\ndata: x\n\n"))      // ad bos satirda sifirlandi
    }

    @Test
    fun cokSatirliDataYeniSatirlaBirlesir() {
        assertEquals(listOf("|bir\niki\n"), ayir("data: bir\ndata: iki\ndata:\n\n"))
    }

    @Test
    fun ikiNoktadanSonraYalnizTekBoslukAtilir() {
        assertEquals(listOf("|x", "| y", "|a:b"), ayir("data:x\n\ndata:  y\n\ndata: a:b\n\n"))
    }

    @Test
    fun crlfVeYalnizCrDeSatirSonudur() {
        assertEquals(listOf("|D 1", "|D 2"), ayir("data: D 1\r\n\r\ndata: D 2\r\n\r\n"))
        assertEquals(listOf("|D 1", "|D 2"), ayir("data: D 1\r\rdata: D 2\r\r"))
        // CR ile LF ayri beslemelere duserse fazladan bos satir SAYILMAZ (olay erken bolunmez)
        val a = SseAyirici()
        assertTrue(a.besle("event: dolu\r".toByteArray()).isEmpty())
        assertEquals(listOf("dolu|4"), ozet(a.besle("\ndata: 4\r\n\r\n".toByteArray())))
    }

    @Test
    fun baytBaytBeslemeAyniSonucuVerir() {
        val metin = "retry: 3000\n\nevent: kimlik\ndata: {\"jeton\":\"abc\"}\n\nid: 1\ndata: D 12.0000 0.5 şğü\r\n\r\n: kalp\n\ndata: G 1\n\n"
        val tek = ayir(metin)
        val a = SseAyirici()
        val parca = ArrayList<SseOlay>()
        for (b in metin.toByteArray(Charsets.UTF_8)) parca.addAll(a.besle(byteArrayOf(b)))
        assertEquals(tek, ozet(parca))
        assertEquals(listOf("kimlik|{\"jeton\":\"abc\"}", "|D 12.0000 0.5 şğü", "|G 1"), tek)
    }

    @Test
    fun besleBasVeUzunlukIleDilimOkur() {
        val b = "XXdata: D 1\n\nYY".toByteArray()
        assertEquals(listOf("|D 1"), ozet(SseAyirici().besle(b, 2, b.size - 4)))
    }

    @Test
    fun satirSiniri4096Bayt_uzunSatirinOlayiAtilirSonrakiSaglam() {
        assertEquals(4096, SseAyirici.SATIR_AZAMI)
        val tam = "data: " + "x".repeat(4096 - 6)
        assertEquals(4096, tam.length)
        assertEquals(listOf("|" + "x".repeat(4090), "|sonra"), ayir("$tam\n\ndata: sonra\n\n"))
        val uzun = tam + "x"
        assertEquals(listOf("|sonra"), ayir("$uzun\n\ndata: sonra\n\n"))
        // uzun satir olayin ortasindaysa olayin TAMAMI atilir (yarim veri tasinmaz)
        assertEquals(listOf("|sonra"), ayir("data: bas\n$uzun\ndata: son\n\ndata: sonra\n\n"))
    }

    @Test
    fun devSatirBellekBuyutmezVeSonrasiSaglam() {
        val a = SseAyirici()
        val parca = ByteArray(65536) { 'x'.code.toByte() }
        for (i in 0 until 64) assertTrue(a.besle(parca).isEmpty())          // 4 MB, satir sonu yok
        assertTrue(a.tamponBoyu() <= SseAyirici.SATIR_AZAMI)
        assertEquals(listOf("|D 1"), ozet(a.besle("\n\ndata: D 1\n\n".toByteArray())))
    }

    @Test
    fun olayVerisiToplamSiniriAsilirsaOlayAtilir() {
        val satir = "data: " + "y".repeat(4000) + "\n"
        assertEquals(listOf("|sonra"), ayir(satir.repeat(5) + "\ndata: sonra\n\n"))     // 20 000 > VERI_AZAMI
        assertEquals(1, SseAyirici().besle((satir.repeat(2) + "\n").toByteArray()).size)
    }

    @Test
    fun bastakiBomAtilir() {
        val b = byteArrayOf(0xEF.toByte(), 0xBB.toByte(), 0xBF.toByte()) + "data: D 1\n\n".toByteArray()
        assertEquals(listOf("|D 1"), ozet(SseAyirici().besle(b)))
    }
}
