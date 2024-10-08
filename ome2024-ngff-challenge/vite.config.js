import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";

let config = {
  plugins: [svelte()],
};
// this will be undefined when deployed from netlify, but is used by gh-pages
if (process.env.GITHUB_REPOSITORY_OWNER) {
  config.base = `https://${process.env.GITHUB_REPOSITORY_OWNER}.github.io/ome2024-ngff-challenge/`;
}

// https://vitejs.dev/config/
export default defineConfig(config);
