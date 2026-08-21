"use client";

import React, { useState, useRef, useEffect } from "react";
import { Mic, Square, Play, Pause, Trash2 } from "lucide-react";

export interface VoiceNoteRecorderProps {
  onRecordingComplete: (blobUrl: string, durationSec: number) => void;
  onCancel: () => void;
}

export function VoiceNoteRecorder({ onRecordingComplete, onCancel }: VoiceNoteRecorderProps) {
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [mediaStream, setMediaStream] = useState<MediaStream | null>(null);
  
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  
  const cleanup = () => {
    if (timerRef.current) clearInterval(timerRef.current);
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
      mediaRecorderRef.current.stop();
    }
    if (mediaStream) {
      mediaStream.getTracks().forEach((track) => track.stop());
    }
  };

  useEffect(() => {
    return cleanup;
  }, [mediaStream]);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      setMediaStream(stream);
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      mediaRecorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        const blobUrl = URL.createObjectURL(blob);
        onRecordingComplete(blobUrl, recordingTime);
        cleanup();
      };

      mediaRecorder.start();
      setIsRecording(true);
      setRecordingTime(0);

      timerRef.current = setInterval(() => {
        setRecordingTime((prev) => {
          if (prev >= 30) {
            stopRecording();
            return prev;
          }
          return prev + 1;
        });
      }, 1000);
    } catch (error) {
      console.warn("Microphone access denied. Using mock recording for DEMO.", error);
      // Fallback for DEMO mode without permissions
      setIsRecording(true);
      setRecordingTime(0);
      timerRef.current = setInterval(() => {
        setRecordingTime((prev) => {
          if (prev >= 5) {
            stopMockRecording();
            return prev;
          }
          return prev + 1;
        });
      }, 1000);
    }
  };

  const stopMockRecording = () => {
    if (timerRef.current) clearInterval(timerRef.current);
    setIsRecording(false);
    // Return a dummy URL for demo purposes
    onRecordingComplete("mock-audio-blob-url", recordingTime || 5);
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stop();
    } else {
      stopMockRecording();
    }
    setIsRecording(false);
    if (timerRef.current) clearInterval(timerRef.current);
  };

  return (
    <div className="flex items-center gap-3 p-2 bg-slate-900/80 rounded-control border border-slate-700">
      {!isRecording ? (
        <button
          onClick={startRecording}
          className="flex items-center justify-center w-8 h-8 rounded-full bg-red-500/20 text-red-400 hover:bg-red-500/30 transition-colors"
          title="Start Recording"
        >
          <Mic size={16} />
        </button>
      ) : (
        <button
          onClick={stopRecording}
          className="flex items-center justify-center w-8 h-8 rounded-full bg-red-500 text-white animate-pulse shadow-[0_0_10px_rgba(239,68,68,0.5)]"
          title="Stop Recording"
        >
          <Square size={12} className="fill-current" />
        </button>
      )}

      <div className="flex-1 font-mono text-xs text-slate-300">
        {isRecording ? (
          <span className="text-red-400 animate-pulse">
            Recording... 00:{recordingTime.toString().padStart(2, "0")}
          </span>
        ) : (
          <span>Click to record voice note (Max 30s)</span>
        )}
      </div>

      <button
        onClick={() => {
          cleanup();
          onCancel();
        }}
        className="p-1.5 text-slate-500 hover:text-slate-300 transition-colors"
        title="Cancel"
      >
        <Trash2 size={16} />
      </button>
    </div>
  );
}

export function AudioPlayer({ blobUrl }: { blobUrl: string }) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);

  useEffect(() => {
    return () => {
      // Cleanup ObjectURL if this component unmounts to prevent memory leaks
      if (blobUrl && blobUrl.startsWith("blob:")) {
        URL.revokeObjectURL(blobUrl);
      }
    };
  }, [blobUrl]);

  const togglePlay = () => {
    if (!audioRef.current) return;
    if (isPlaying) {
      audioRef.current.pause();
    } else {
      if (blobUrl === "mock-audio-blob-url") {
        setIsPlaying(true);
        setTimeout(() => setIsPlaying(false), 5000); // Simulate 5s play
      } else {
        audioRef.current.play();
      }
    }
    setIsPlaying(!isPlaying);
  };

  return (
    <div className="flex items-center gap-2 p-1.5 bg-slate-950/50 rounded-control border border-slate-700/50 mt-1 max-w-[200px]">
      <button
        onClick={togglePlay}
        className="flex items-center justify-center w-6 h-6 rounded-full bg-cyan-500/20 text-cyan-400 hover:bg-cyan-500/30"
      >
        {isPlaying ? <Pause size={12} /> : <Play size={12} className="ml-0.5" />}
      </button>
      <div className="flex-1 flex items-center gap-0.5">
        {[...Array(12)].map((_, i) => (
          <div
            key={i}
            className={`w-1 rounded-full bg-cyan-500/50 transition-all ${
              isPlaying ? "animate-pulse" : ""
            }`}
            style={{
              height: `${Math.max(4, Math.random() * 16)}px`,
              animationDelay: `${i * 0.1}s`,
            }}
          />
        ))}
      </div>
      {blobUrl !== "mock-audio-blob-url" && (
        <audio
          ref={audioRef}
          src={blobUrl}
          onEnded={() => setIsPlaying(false)}
          className="hidden"
        />
      )}
    </div>
  );
}
