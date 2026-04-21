import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  // base: "/codeboard/",  <-- Ise hata do agar aap custom domain/root par ho
  server: {
    port: 5173,
  },
});