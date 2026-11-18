import { defineConfig } from "vite";
import path from "node:path";
import react from "@vitejs/plugin-react";
import svgr from "vite-plugin-svgr";

console.log("process.env.NODE_ENV", process.env.NODE_ENV);

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => ({
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
    include: [
      "src/**/*.{test,spec}.{js,jsx,ts,tsx}",
      "../dj-be/survey_designer/apps/questions/tests/js/**/*.test.js",
    ],
    setupFiles: ["src/app/setupTests.js"],
    exclude: ["e2e/**", "node_modules/**", "dist/**"],
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
    ...(mode === "test"
      ? {
          fs: {
            allow: [
              path.resolve(
                __dirname,
                "../dj-be/survey_designer/apps/questions/tests/js",
              ),
            ],
          },
        }
      : {}),
  },
  plugins: [
    react(),
    svgr(),
  ],
}));
