"use client";

import { useEffect, useState, useRef } from "react";
import { getSiteConfig } from "@/lib/api";

export default function HeroVideo() {
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(false);
  const [isMuted, setIsMuted] = useState(true);
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    async function fetchVideoUrl() {
      try {
        const config = await getSiteConfig();
        setVideoUrl(config.hero_video_url);
      } catch (err) {
        console.error("Failed to fetch hero video config:", err);
        setError(true);
      } finally {
        setIsLoading(false);
      }
    }

    fetchVideoUrl();
  }, []);

  const handleVideoLoad = () => {
    setIsLoading(false);
  };

  const toggleMute = () => {
    if (videoRef.current) {
      videoRef.current.muted = !videoRef.current.muted;
      setIsMuted(videoRef.current.muted);
    }
  };

  return (
    <section className="relative w-full h-[40vh] sm:h-[50vh] md:h-[60vh] lg:h-[70vh] overflow-hidden bg-white">
      {/* Video */}
      {videoUrl && !error && (
        <video
          ref={videoRef}
          className="w-full h-full object-contain sm:object-cover"
          autoPlay
          loop
          muted
          playsInline
          onLoadedData={handleVideoLoad}
        >
          <source src={videoUrl} type="video/mp4" />
        </video>
      )}

      {/* Sound toggle button */}
      {videoUrl && !error && !isLoading && (
        <button
          onClick={toggleMute}
          className="absolute bottom-2 right-2 sm:bottom-4 sm:right-4 z-10 bg-black/50 hover:bg-black/70 text-white p-2 sm:p-3 rounded-full transition-colors"
          aria-label={isMuted ? "Unmute" : "Mute"}
        >
          {isMuted ? (
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="sm:w-5 sm:h-5">
              <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
              <line x1="23" y1="9" x2="17" y2="15" />
              <line x1="17" y1="9" x2="23" y2="15" />
            </svg>
          ) : (
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="sm:w-5 sm:h-5">
              <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
              <path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07" />
            </svg>
          )}
        </button>
      )}

      {/* Loading state */}
      {isLoading && (
        <div className="absolute inset-0 bg-white flex items-center justify-center">
          <div className="w-6 h-6 sm:w-8 sm:h-8 border-2 border-black border-t-transparent rounded-full animate-spin" />
        </div>
      )}

      {/* Fallback for error state */}
      {error && !isLoading && (
        <div className="absolute inset-0 bg-gray-100" />
      )}
    </section>
  );
}
