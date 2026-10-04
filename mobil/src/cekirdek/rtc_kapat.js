// WebRTC'yi kapatir. Olculdu (2026-10-04, Android 13, WebView 153): CSP `webrtc 'block'` yonergesi
// UYGULANMIYOR; CSP'nin oteki yonergeleri ve yerel istek kapisi (WebKapi) da WebRTC'yi kapsamaz.
// Bu yuzden arayuzlerin KENDISI kaldirilir: once yerel taraf belge basinda (MainActivity,
// addDocumentStartJavaScript — WebKapi.RTC_KAPAT, bu listeyle AYNI adlar), sonra burada, uygulamanin
// ILK ice aktarimi olarak (yerel ozellik desteklenmiyorsa yedek).
export const RTC_ADLARI = Object.freeze([
  "RTCPeerConnection", "webkitRTCPeerConnection", "RTCDataChannel", "RTCSessionDescription",
  "RTCIceCandidate", "RTCRtpSender", "RTCRtpReceiver", "RTCRtpTransceiver",
]);

export function rtcKapat(hedef = globalThis) {
  for (const ad of RTC_ADLARI) {
    try {
      Object.defineProperty(hedef, ad, { value: undefined, writable: false, configurable: false });
    } catch { /* zaten kilitli */ }
  }
}

rtcKapat();
