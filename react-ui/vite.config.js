import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import svgr from "vite-plugin-svgr";

console.log("process.env.NODE_ENV", process.env.NODE_ENV);

// https://vitejs.dev/config/
export default defineConfig({
  build: {
    manifest: true,
    // outDir: "../static/"
  },
  modulePreload: {
    polyfill: true,
  },
  envDir: ".",
  base:  "/",
  test: {
    globals: true,
    environment: "jsdom",
    reporters: ["default", "junit"],
    outputFile: "test-results.xml",
    coverage: {
      reportsDirectory: "./coverage",
      reporter: ["text", "cobertura"],
    },
    // you might want to disable it, if you don't have tests that rely on CSS
    // since parsing CSS is slow
    css: true,
  },
  server: {
    port: 3000,
  },
  plugins: [
    react(),
    svgr(),
  ],
});
