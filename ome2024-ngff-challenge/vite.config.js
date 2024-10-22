import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";

import { existsSync, mkdirSync, copyFileSync } from "fs";
import { resolve as pathResolve, join as pathJoin } from "path";

// https://dev.to/patarapolw/vite-on-github-pages-with-html5-history-mode-283j
// We want to clone `index.html` to all routes, e.g. /about/index.html
function cloneIndexHtmlPlugin(routes = []) {
  const name = "CloneIndexHtmlPlugin";
  const outDir = "dist"; // config's `build.outDir`
  const src = pathJoin(outDir, "index.html");

  return {
    name,
    closeBundle: () => {
      routes.push("about");

      routes.map((p) => {
        const dir = pathResolve(outDir, p);
        if (!existsSync(dir)) {
          mkdirSync(dir, { recursive: true });
        }

        const dst = pathJoin(outDir, p, "index.html");

        // It is possible to edit HTML here, too.
        copyFileSync(src, dst);
        console.log(`${name}: Copied ${src} to ${dst}`);
      });
    },
  };
}

let config = {
  plugins: [svelte(), cloneIndexHtmlPlugin()],
};
// this will be undefined when deployed from netlify, but is used by gh-pages
if (process.env.GITHUB_REPOSITORY_OWNER) {
  config.base = `https://${process.env.GITHUB_REPOSITORY_OWNER}.github.io/ome2024-ngff-challenge/`;
}

// https://vitejs.dev/config/
export default defineConfig(config);
