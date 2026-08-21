"use client";

import React, { useEffect, useState, useRef } from "react";
import Link from "next/link";
import { ArrowLeft, Send, Users, ShieldAlert } from "lucide-react";
import { TrackMap } from "../../../components/map/TrackMap";
import { VideoPlayer } from "../../../components/video/VideoPlayer";
import { useCollabStore } from "../../../stores/collab-store";
import { VoiceNoteRecorder, AudioPlayer } from "../../../components/collab/VoiceNoteRecorder";
import { useModeStore } from "../../../stores/mode-store";
import type { Annotation } from "@trackchain/shared";

export default function WarRoomPage({ params }: { params: { id: string } }) {
  const incidentId = params.id;
  const collabStore = useCollabStore();
  const { mode } = useModeStore();
  const threadEndRef = useRef<HTMLDivElement>(null);

  const [inputText, setInputText] = useState("");
  const [showVoiceRecorder, setShowVoiceRecorder] = useState(false);

  // Trigger deterministic demo sequence if in DEMO mode
  useEffect(() => {
    if (mode === "DEMO") {
      collabStore.simulatePresence();
    }
  }, [mode]);

  // Auto-scroll to bottom of thread on new message
  useEffect(() => {
    threadEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [collabStore.annotations]);

  const handleSendText = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim()) return;

    // Basic @mention extraction
    const mentions = inputText.match(/@\w+/g) || [];

    collabStore.addAnnotation({
      id: `ann-in-${Date.now()}`,
      type: "INCIDENT",
      target_id: incidentId,
      author: {
        id: "u-me",
        name: "You",
        role: "Incident Commander",
        avatarColor: "bg-cyan-500",
        status: "online",
      },
      text: inputText,
      mentions,
      created_at: Date.now(),
    });
    setInputText("");
  };

  const handleVoiceNoteComplete = (blobUrl: string, durationSec: number) => {
    collabStore.addAnnotation({
      id: `ann-vn-${Date.now()}`,
      type: "INCIDENT",
      target_id: incidentId,
      author: {
        id: "u-me",
        name: "You",
        role: "Incident Commander",
        avatarColor: "bg-cyan-500",
        status: "online",
      },
      text: `Sent a voice note (${durationSec}s)`,
      audio_blob_url: blobUrl,
      mentions: [],
      created_at: Date.now(),
    });
    setShowVoiceRecorder(false);
  };

  // Helper to highlight @mentions
  const renderTextWithMentions = (text: string) => {
    const parts = text.split(/(@\w+)/g);
    return parts.map((part, i) =>
      part.startsWith("@") ? (
        <span key={i} className="text-cyan-400 font-bold bg-cyan-900/30 px-1 rounded">
          {part}
        </span>
      ) : (
        part
      )
    );
  };

  return (
    <div className="flex flex-col h-screen bg-[#020617] text-slate-200 overflow-hidden font-sans">
      {/* War Room Header */}
      <header className="flex-shrink-0 flex items-center justify-between h-14 px-4 border-b border-scada-border bg-slate-950/80 backdrop-blur">
        <div className="flex items-center gap-4">
          <Link
            href="/"
            className="flex items-center gap-2 text-slate-400 hover:text-white transition-colors text-xs font-mono"
          >
            <ArrowLeft size={16} />
            <span>EXIT ROOM</span>
          </Link>
          <div className="h-6 w-px bg-slate-800" />
          <div className="flex items-center gap-2">
            <ShieldAlert size={18} className="text-red-500" />
            <h1 className="font-bold text-sm tracking-wider uppercase">
              WAR ROOM: {incidentId}
            </h1>
            <span className="badge-red animate-pulse text-[10px]">CRITICAL</span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Active Presence Avatars */}
          <div className="flex items-center">
            {collabStore.presence.map((user, i) => (
              <div
                key={user.id}
                className={`relative -ml-2 flex h-8 w-8 items-center justify-center rounded-full border-2 border-slate-950 text-[10px] font-bold text-white shadow-md ${user.avatarColor}`}
                style={{ zIndex: 10 - i }}
                title={`${user.name} (${user.role})`}
              >
                {user.name.charAt(0)}
                <span className="absolute bottom-0 right-0 h-2 w-2 rounded-full bg-emerald-500 border border-slate-950" />
              </div>
            ))}
            <div className="relative -ml-2 flex h-8 w-8 items-center justify-center rounded-full border-2 border-slate-950 bg-slate-800 text-[10px] font-bold text-slate-400 shadow-md z-0 cursor-pointer hover:bg-slate-700">
              <Users size={14} />
            </div>
          </div>
          <button className="rounded-control bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 px-3 py-1.5 text-[10px] font-mono font-bold hover:bg-cyan-500/20 transition-all">
            + INVITE
          </button>
        </div>
      </header>

      {/* 3-Pane Grid Layout */}
      <main className="flex-1 grid grid-cols-1 lg:grid-cols-2 grid-rows-2 lg:grid-rows-1 overflow-hidden">
        {/* Left (50%): GIS Map */}
        <section className="col-span-1 border-r border-scada-border h-full flex flex-col relative">
          <div className="absolute top-4 left-4 z-20 flex items-center gap-2 px-3 py-1.5 bg-slate-900/90 border border-slate-700 rounded-control backdrop-blur shadow-xl">
            <span className="h-2 w-2 rounded-full bg-cyan-400 animate-pulse" />
            <span className="font-mono text-[10px] font-bold text-slate-300">SPATIAL CONTEXT</span>
          </div>
          <TrackMap className="flex-1 rounded-none border-none h-full !bg-[#020617]" />
        </section>

        {/* Right (50%): Top Video, Bottom Thread */}
        <section className="col-span-1 grid grid-rows-2 h-full bg-[#030914]">
          {/* Top (25% total): Temporal Context */}
          <div className="border-b border-scada-border h-full flex flex-col p-2 relative bg-slate-950">
            <div className="absolute top-4 left-4 z-20 flex items-center gap-2 px-3 py-1.5 bg-slate-900/90 border border-slate-700 rounded-control backdrop-blur shadow-xl">
              <span className="h-2 w-2 rounded-full bg-purple-400 animate-pulse" />
              <span className="font-mono text-[10px] font-bold text-slate-300">TEMPORAL CONTEXT</span>
            </div>
            <VideoPlayer src="" className="h-full rounded-none border-none !bg-transparent" />
          </div>

          {/* Bottom (25% total): Collaboration Thread */}
          <div className="h-full flex flex-col bg-[#050c1a]">
            {/* Thread Header */}
            <div className="px-4 py-2 border-b border-white/5 bg-slate-900/50">
              <h3 className="font-mono text-[11px] font-bold text-slate-400">INCIDENT THREAD</h3>
            </div>

            {/* Messages Scroll Area */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {collabStore.annotations.map((ann) => (
                <div key={ann.id} className="flex gap-3">
                  <div
                    className={`shrink-0 flex h-7 w-7 items-center justify-center rounded-full text-[10px] font-bold text-white shadow-md ${ann.author.avatarColor}`}
                  >
                    {ann.author.name.charAt(0)}
                  </div>
                  <div className="flex flex-col flex-1">
                    <div className="flex items-baseline gap-2">
                      <span className="font-bold text-xs text-slate-200">
                        {ann.author.name}
                      </span>
                      <span className="font-mono text-[10px] text-slate-500">
                        {new Date(ann.created_at).toLocaleTimeString()}
                      </span>
                      {ann.type === "SPATIAL" && (
                        <span className="badge-cyan text-[8px] py-0">📍 MAP PIN</span>
                      )}
                      {ann.type === "TEMPORAL" && (
                        <span className="badge-purple text-[8px] py-0">▲ t={ann.timestamp_sec}s</span>
                      )}
                    </div>
                    <div className="mt-1 text-sm text-slate-300 bg-slate-900/40 p-2 rounded-lg border border-white/5 shadow-inner leading-relaxed">
                      {renderTextWithMentions(ann.text)}
                      {ann.audio_blob_url && (
                        <AudioPlayer blobUrl={ann.audio_blob_url} />
                      )}
                    </div>
                  </div>
                </div>
              ))}
              <div ref={threadEndRef} />
            </div>

            {/* Composer Input */}
            <div className="p-3 border-t border-scada-border bg-slate-950/80 backdrop-blur">
              {showVoiceRecorder ? (
                <VoiceNoteRecorder
                  onRecordingComplete={handleVoiceNoteComplete}
                  onCancel={() => setShowVoiceRecorder(false)}
                />
              ) : (
                <form onSubmit={handleSendText} className="flex items-center gap-2">
                  <input
                    type="text"
                    value={inputText}
                    onChange={(e) => setInputText(e.target.value)}
                    placeholder="Type a message or use @ to mention..."
                    className="flex-1 bg-slate-900 border border-slate-700 rounded-control px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition-all placeholder:text-slate-600"
                  />
                  <button
                    type="button"
                    onClick={() => setShowVoiceRecorder(true)}
                    className="p-2 text-slate-400 hover:text-cyan-400 hover:bg-cyan-500/10 rounded-control transition-colors"
                    title="Record Voice Note"
                  >
                    <MicIcon size={18} />
                  </button>
                  <button
                    type="submit"
                    disabled={!inputText.trim()}
                    className="p-2 bg-cyan-600 text-white rounded-control hover:bg-cyan-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-[0_0_10px_rgba(8,145,178,0.3)]"
                  >
                    <Send size={18} />
                  </button>
                </form>
              )}
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}

// Separate component for MicIcon to avoid importing Mic in this file directly
function MicIcon({ size }: { size: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
      <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
      <line x1="12" x2="12" y1="19" y2="22" />
    </svg>
  );
}
