/**
 * Workflow 1 — Citizen Reporting
 *
 * Open → Capture Photo → Record Voice → Enter Text → Location → Review → Submit → Progress → Success
 *
 * UI Principles:
 * - Under 60 seconds from open to submit
 * - Maps first, text second
 * - Every screen answers one question
 * - Never overwhelm
 */

import { useState, useRef, useCallback, useEffect } from "react";
import { useStore } from "../store";
import { submitObservation } from "../api";
import type { ObservationCategory } from "../types";

const CATEGORIES: { value: ObservationCategory; label: string; icon: string }[] = [
  { value: "smoke", label: "Smoke", icon: "💨" },
  { value: "fire", label: "Fire", icon: "🔥" },
  { value: "dust", label: "Dust", icon: "🌫️" },
  { value: "chemical", label: "Chemical", icon: "⚗️" },
  { value: "water", label: "Water", icon: "💧" },
  { value: "noise", label: "Noise", icon: "🔊" },
  { value: "gas_leak", label: "Gas Leak", icon: "⚠️" },
  { value: "construction_dust", label: "Construction", icon: "🏗️" },
  { value: "sewage", label: "Sewage", icon: "🚰" },
  { value: "other", label: "Other", icon: "❓" },
];

const LANGUAGES = [
  { code: "en", label: "English" },
  { code: "hi", label: "हिन्दी" },
  { code: "mr", label: "मराठी" },
];

type Step = "photo" | "voice" | "text" | "location" | "review" | "submitting" | "success";

export default function CitizenFlow() {
  const { draft, setDraft, resetDraft } = useStore();
  const [step, setStep] = useState<Step>("photo");
  const [trackingRef, setTrackingRef] = useState("");
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const [recording, setRecording] = useState(false);

  // Get location on mount
  useEffect(() => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => setDraft({ latitude: pos.coords.latitude, longitude: pos.coords.longitude }),
        () => {} // Silently fail — user can enter manually
      );
    }
  }, [setDraft]);

  const handlePhotoCapture = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handlePhotoSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) {
        setDraft({ photo: file });
        setStep("voice");
      }
    },
    [setDraft]
  );

  const toggleRecording = useCallback(async () => {
    if (recording) {
      mediaRecorderRef.current?.stop();
      setRecording(false);
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      const chunks: Blob[] = [];
      recorder.ondataavailable = (e) => chunks.push(e.data);
      recorder.onstop = () => {
        setDraft({ voice: new Blob(chunks, { type: "audio/webm" }) });
        stream.getTracks().forEach((t) => t.stop());
      };
      mediaRecorderRef.current = recorder;
      recorder.start();
      setRecording(true);
    } catch {
      // Mic not available — skip
      setStep("text");
    }
  }, [recording, setDraft]);

  const handleSubmit = async () => {
    if (!draft.latitude || !draft.longitude) {
      setError("Location is required");
      return;
    }
    if (!draft.content && !draft.photo) {
      setError("Please add a photo or description");
      return;
    }

    setStep("submitting");
    setUploading(true);
    setError("");

    try {
      // Simulate upload progress
      const progressInterval = setInterval(() => {
        setUploadProgress((p) => Math.min(p + 15, 90));
      }, 200);

      const result = await submitObservation({
        content: draft.content || "Environmental observation",
        latitude: draft.latitude,
        longitude: draft.longitude,
        category: draft.category as ObservationCategory,
        language: draft.language as "en" | "hi" | "mr",
        device_id: `web-${Date.now()}`,
      });

      clearInterval(progressInterval);
      setUploadProgress(100);
      setTrackingRef(result.tracking_ref);
      setStep("success");
      resetDraft();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Submission failed");
      setStep("review");
    } finally {
      setUploading(false);
    }
  };

  // --- Step renderers ---

  if (step === "success") {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
        <div className="text-6xl mb-4">✅</div>
        <h2 className="text-2xl font-bold text-emerald-400 mb-2">Observation Submitted</h2>
        <p className="text-gray-400 mb-4">Your observation has been received and is being processed.</p>
        <div className="bg-gray-800 rounded-lg px-6 py-4 mb-6">
          <p className="text-sm text-gray-400">Tracking Reference</p>
          <p className="text-2xl font-mono font-bold text-white">{trackingRef}</p>
        </div>
        <button
          onClick={() => { setStep("photo"); setTrackingRef(""); }}
          className="px-6 py-2 bg-emerald-600 hover:bg-emerald-700 rounded-lg font-medium transition-colors"
        >
          Submit Another
        </button>
      </div>
    );
  }

  if (step === "submitting") {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
        <div className="text-4xl mb-4 animate-pulse">📡</div>
        <h2 className="text-xl font-bold mb-4">Submitting Observation...</h2>
        <div className="w-64 bg-gray-800 rounded-full h-3 mb-2">
          <div
            className="bg-emerald-500 h-3 rounded-full transition-all duration-300"
            style={{ width: `${uploadProgress}%` }}
          />
        </div>
        <p className="text-sm text-gray-400">{uploadProgress}%</p>
        {error && <p className="text-red-400 mt-4">{error}</p>}
      </div>
    );
  }

  const stepIndex = ["photo", "voice", "text", "location", "review"].indexOf(step);
  const totalSteps = 5;

  return (
    <div className="max-w-lg mx-auto">
      {/* Progress bar */}
      <div className="flex items-center gap-2 mb-6">
        {Array.from({ length: totalSteps }, (_, i) => (
          <div
            key={i}
            className={`h-1 flex-1 rounded ${
              i <= stepIndex ? "bg-emerald-500" : "bg-gray-700"
            }`}
          />
        ))}
      </div>

      {/* Language selector */}
      <div className="flex gap-2 mb-6">
        {LANGUAGES.map((lang) => (
          <button
            key={lang.code}
            onClick={() => setDraft({ language: lang.code })}
            className={`px-3 py-1 text-sm rounded ${
              draft.language === lang.code
                ? "bg-emerald-600 text-white"
                : "bg-gray-800 text-gray-400 hover:bg-gray-700"
            }`}
          >
            {lang.label}
          </button>
        ))}
      </div>

      {/* Step content */}
      {step === "photo" && (
        <div className="text-center">
          <h2 className="text-xl font-bold mb-2">Capture Evidence</h2>
          <p className="text-gray-400 mb-6">Take a photo of what you observe</p>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            capture="environment"
            className="hidden"
            onChange={handlePhotoSelect}
          />
          <button
            onClick={handlePhotoCapture}
            className="w-32 h-32 rounded-full bg-gray-800 hover:bg-gray-700 border-4 border-emerald-500 flex items-center justify-center text-4xl transition-colors mx-auto"
          >
            📷
          </button>
          {draft.photo && (
            <p className="text-emerald-400 mt-4 text-sm">✓ Photo captured</p>
          )}
          <button
            onClick={() => setStep("voice")}
            className="mt-4 text-sm text-gray-500 hover:text-gray-300"
          >
            Skip photo →
          </button>
        </div>
      )}

      {step === "voice" && (
        <div className="text-center">
          <h2 className="text-xl font-bold mb-2">Record Voice Note</h2>
          <p className="text-gray-400 mb-6">Describe what you see (optional)</p>
          <button
            onClick={toggleRecording}
            className={`w-24 h-24 rounded-full flex items-center justify-center text-3xl transition-all ${
              recording
                ? "bg-red-600 animate-pulse scale-110"
                : "bg-gray-800 hover:bg-gray-700 border-4 border-gray-600"
            }`}
          >
            {recording ? "⏹️" : "🎙️"}
          </button>
          {recording && <p className="text-red-400 mt-2 text-sm animate-pulse">Recording...</p>}
          {draft.voice && <p className="text-emerald-400 mt-4 text-sm">✓ Voice recorded</p>}
          <div className="flex gap-3 justify-center mt-6">
            <button
              onClick={() => setStep("text")}
              className="px-4 py-2 text-sm text-gray-400 hover:text-white"
            >
              Skip →
            </button>
          </div>
        </div>
      )}

      {step === "text" && (
        <div>
          <h2 className="text-xl font-bold mb-2">Describe What You See</h2>
          <p className="text-gray-400 mb-4">What is happening? (optional)</p>
          <textarea
            value={draft.content}
            onChange={(e) => setDraft({ content: e.target.value })}
            placeholder="I see heavy smoke coming from..."
            className="w-full h-32 bg-gray-800 border border-gray-700 rounded-lg p-3 text-white placeholder-gray-500 focus:border-emerald-500 focus:outline-none resize-none"
          />
          <div className="mt-4">
            <p className="text-sm text-gray-400 mb-2">What type of event?</p>
            <div className="grid grid-cols-5 gap-2">
              {CATEGORIES.map((cat) => (
                <button
                  key={cat.value}
                  onClick={() => setDraft({ category: cat.value })}
                  className={`p-2 rounded-lg text-center text-xs transition-colors ${
                    draft.category === cat.value
                      ? "bg-emerald-600 text-white"
                      : "bg-gray-800 text-gray-400 hover:bg-gray-700"
                  }`}
                >
                  <span className="text-lg block">{cat.icon}</span>
                  {cat.label}
                </button>
              ))}
            </div>
          </div>
          <button
            onClick={() => setStep("location")}
            className="mt-6 w-full py-3 bg-emerald-600 hover:bg-emerald-700 rounded-lg font-medium transition-colors"
          >
            Next: Location →
          </button>
        </div>
      )}

      {step === "location" && (
        <div>
          <h2 className="text-xl font-bold mb-2">Confirm Location</h2>
          <p className="text-gray-400 mb-4">Where is this happening?</p>

          {/* Simple map placeholder */}
          <div className="bg-gray-800 rounded-lg h-48 flex items-center justify-center mb-4 relative overflow-hidden">
            <div className="text-center">
              <p className="text-2xl mb-1">📍</p>
              {draft.latitude !== null ? (
                <>
                  <p className="text-sm text-emerald-400">Location detected</p>
                  <p className="text-xs text-gray-500">
                    {draft.latitude.toFixed(4)}, {draft.longitude?.toFixed(4)}
                  </p>
                </>
              ) : (
                <p className="text-sm text-gray-400">Waiting for GPS...</p>
              )}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3 mb-4">
            <div>
              <label className="text-xs text-gray-400 block mb-1">Latitude</label>
              <input
                type="number"
                step="any"
                value={draft.latitude ?? ""}
                onChange={(e) => setDraft({ latitude: parseFloat(e.target.value) || null })}
                className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="text-xs text-gray-400 block mb-1">Longitude</label>
              <input
                type="number"
                step="any"
                value={draft.longitude ?? ""}
                onChange={(e) => setDraft({ longitude: parseFloat(e.target.value) || null })}
                className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
              />
            </div>
          </div>

          <button
            onClick={() => navigator.geolocation?.getCurrentPosition(
              (pos) => setDraft({ latitude: pos.coords.latitude, longitude: pos.coords.longitude }),
              () => {}
            )}
            className="w-full py-2 text-sm text-emerald-400 hover:text-emerald-300 border border-gray-700 rounded-lg mb-4"
          >
            🔄 Re-detect location
          </button>

          <button
            onClick={() => setStep("review")}
            className="w-full py-3 bg-emerald-600 hover:bg-emerald-700 rounded-lg font-medium transition-colors"
          >
            Next: Review →
          </button>
        </div>
      )}

      {step === "review" && (
        <div>
          <h2 className="text-xl font-bold mb-4">Review Your Observation</h2>

          <div className="space-y-3">
            {draft.photo && (
              <div className="bg-gray-800 rounded-lg p-3 flex items-center gap-3">
                <span className="text-2xl">📷</span>
                <div>
                  <p className="text-sm font-medium">Photo</p>
                  <p className="text-xs text-gray-400">{draft.photo.name}</p>
                </div>
              </div>
            )}

            {draft.voice && (
              <div className="bg-gray-800 rounded-lg p-3 flex items-center gap-3">
                <span className="text-2xl">🎙️</span>
                <div>
                  <p className="text-sm font-medium">Voice Note</p>
                  <p className="text-xs text-gray-400">Recorded</p>
                </div>
              </div>
            )}

            {draft.content && (
              <div className="bg-gray-800 rounded-lg p-3">
                <p className="text-sm text-gray-400 mb-1">Description</p>
                <p className="text-sm">{draft.content}</p>
              </div>
            )}

            <div className="bg-gray-800 rounded-lg p-3 flex items-center gap-3">
              <span className="text-2xl">
                {CATEGORIES.find((c) => c.value === draft.category)?.icon}
              </span>
              <div>
                <p className="text-sm font-medium">
                  {CATEGORIES.find((c) => c.value === draft.category)?.label}
                </p>
                <p className="text-xs text-gray-400">Category</p>
              </div>
            </div>

            <div className="bg-gray-800 rounded-lg p-3 flex items-center gap-3">
              <span className="text-2xl">📍</span>
              <div>
                <p className="text-sm font-medium">Location</p>
                <p className="text-xs text-gray-400">
                  {draft.latitude?.toFixed(4)}, {draft.longitude?.toFixed(4)}
                </p>
              </div>
            </div>
          </div>

          {error && <p className="text-red-400 text-sm mt-3">{error}</p>}

          <button
            onClick={handleSubmit}
            disabled={uploading}
            className="w-full mt-6 py-3 bg-emerald-600 hover:bg-emerald-700 disabled:bg-gray-700 rounded-lg font-medium transition-colors"
          >
            Submit Observation
          </button>
          <button
            onClick={() => setStep("photo")}
            className="w-full mt-2 py-2 text-sm text-gray-400 hover:text-white"
          >
            ← Edit
          </button>
        </div>
      )}
    </div>
  );
}
