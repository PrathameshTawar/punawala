import { useEffect, useRef, useState } from "react";

export default function VideoCall({ onAudioReady, isRecording }) {
  const videoRef = useRef();
  const streamRef = useRef();
  const [countdown, setCountdown] = useState(null);

  const captureFrame = () => {
    if (!videoRef.current) return null;
    const canvas = document.createElement('canvas');
    canvas.width = videoRef.current.videoWidth;
    canvas.height = videoRef.current.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(videoRef.current, 0, 0);
    return new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.8));
  };

  useEffect(() => {
    navigator.mediaDevices
      .getUserMedia({ video: true, audio: true })
      .then((stream) => {
        streamRef.current = stream;
        if (videoRef.current) videoRef.current.srcObject = stream;
      })
      .catch(() => {});
    return () => streamRef.current?.getTracks().forEach((t) => t.stop());
  }, []);

  useEffect(() => {
    if (!isRecording || !streamRef.current) return;

    const recorder = new MediaRecorder(streamRef.current);
    const chunks = [];
    let secs = 5;
    setCountdown(secs);

    const iv = setInterval(() => {
      secs -= 1;
      setCountdown(secs);
      if (secs <= 0) clearInterval(iv);
    }, 1000);

    recorder.ondataavailable = (e) => chunks.push(e.data);
    recorder.onstop = async () => {
      clearInterval(iv);
      setCountdown(null);
      const audioBlob = new Blob(chunks, { type: "audio/wav" });
      const frameBlob = await captureFrame();
      onAudioReady(audioBlob, frameBlob);
    };

    recorder.start();
    setTimeout(() => recorder.state === "recording" && recorder.stop(), 5000);

    return () => clearInterval(iv);
  }, [isRecording]);

  return (
    <div style={{ position: "relative", background: "#060d1a", borderRadius: 12, overflow: "hidden" }}>
      <video
        ref={videoRef}
        autoPlay
        muted
        style={{ width: "100%", display: "block", minHeight: 220, objectFit: "cover" }}
      />

      {/* Live badge */}
      <div style={{
        position: "absolute", top: 12, left: 12,
        display: "flex", alignItems: "center", gap: 6,
        background: "rgba(6,13,26,0.75)", borderRadius: 999,
        padding: "4px 10px", backdropFilter: "blur(6px)",
      }}>
        <span className={`live-dot ${isRecording ? "" : "red"}`} />
        <span style={{ fontSize: 11, fontWeight: 700, color: isRecording ? "#22c55e" : "#ef4444" }}>
          {isRecording ? "RECORDING" : "LIVE"}
        </span>
      </div>

      {/* Countdown */}
      {countdown !== null && (
        <div style={{
          position: "absolute", bottom: 12, right: 12,
          background: "rgba(6,13,26,0.8)", borderRadius: 8,
          padding: "4px 12px", fontSize: 20, fontWeight: 800, color: "#38bdf8",
        }}>
          {countdown}s
        </div>
      )}
    </div>
  );
}
