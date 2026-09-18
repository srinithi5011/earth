import React, { useEffect, useRef } from "react";
import mapboxgl from "mapbox-gl";
import "mapbox-gl/dist/mapbox-gl.css";

// Supply your Mapbox access token here or via process.env.VITE_MAPBOX_TOKEN
mapboxgl.accessToken = "YOUR_MAPBOX_ACCESS_TOKEN";

interface ForestGlobeMapProps {
  center: [number, number]; // [lat, lng]
  zoom?: number;
  region?: string;
}

export default function ForestGlobeMap({ center, zoom = 1.5, region }: ForestGlobeMapProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<mapboxgl.Map | null>(null);

  useEffect(() => {
    if (!mapContainerRef.current) return;

    // Initialize 3D Globe Projection
    const map = new mapboxgl.Map({
      container: mapContainerRef.current,
      style: "mapbox://styles/mapbox/satellite-v9", // High-res satellite style
      center: [center[1], center[0]], // Mapbox requires [lng, lat]
      zoom: zoom,
      projection: "globe" as any, // Turns 2D map into a 3D Earth sphere
    });

    map.on("style.load", () => {
      // Add realistic atmospheric glow & space background
      map.setFog({
        color: "rgb(186, 210, 235)",
        "high-color": "rgb(36, 92, 223)",
        "space-color": "rgb(11, 11, 25)",
        "star-intensity": 0.6,
      });
    });

    if (region) {
      new mapboxgl.Marker({ color: "#16a34a" })
        .setLngLat([center[1], center[0]])
        .setPopup(new mapboxgl.Popup().setHTML(`<b>${region}</b>`))
        .addTo(map);
    }

    mapInstanceRef.current = map;

    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
  }, []);

  // Smoothly fly to new coordinates when user changes location presets
  useEffect(() => {
    if (mapInstanceRef.current) {
      mapInstanceRef.current.flyTo({
        center: [center[1], center[0]],
        zoom: zoom,
        duration: 2000,
      });
    }
  }, [center[0], center[1], zoom]);

  return <div ref={mapContainerRef} className="w-full h-full rounded-xl overflow-hidden" />;
}