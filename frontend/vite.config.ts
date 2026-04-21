import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  // assetsInclude wali line hata di hai kyunki CSS default handle hoti hai
  build: {
    outDir: 'dist',
    sourcemap: false,
  },
});