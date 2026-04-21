import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  // Agar ye line nahi hai toh ise add karo
  assetsInclude: ['**/*.css'], 
  build: {
    rollupOptions: {
      output: {
        // Isse cache clear hota hai aur naya build banta hai
        manualChunks: undefined,
      },
    },
  },
});