/*
 * Render-USD Learning Guide — 导航单一事实源 (single source of truth)
 *
 * 经典 script（非 module），直接挂到 window.BOOK，
 * 在 file:// 与本地 http server 下都能工作，无需打包构建。
 */
window.BOOK = {
  title: "Render-USD Learning Guide",
  subtitle: "From GAMES101 to a Production USD Rendering Pipeline",
  repoUrl: "https://github.com/jandan138/render-usd",
  parts: [
    {
      n: "00",
      title: "导论 · Orientation",
      chapters: [
        {
          id: "0",
          num: "0",
          title: "从课堂渲染器到 production pipeline",
          sections: [
            { id: "0-1", t: "你的 GAMES101 渲染器到哪为止", href: "chapters/00-orientation/0-1-classroom-renderer.html" },
            { id: "0-2", t: "production rendering 全景：the thumbnail journey", href: "chapters/00-orientation/0-2-thumbnail-journey.html" },
            { id: "0-3", t: "认识案例：render-usd 与它的工程问题", href: "chapters/00-orientation/0-3-meet-render-usd.html" },
          ],
        },
      ],
    },
    {
      n: "I",
      title: "技术栈全景 · The Stack",
      chapters: [
        {
          id: "1",
          num: "1",
          title: "Omniverse / Isaac Sim / Carbonite 生态位",
          sections: [
            { id: "1-1", t: "NVIDIA Omniverse 平台架构", href: "chapters/01-stack/1-1-omniverse.html" },
            { id: "1-2", t: "Isaac Sim：仿真与渲染的交汇点", href: "chapters/01-stack/1-2-isaac-sim.html" },
            { id: "1-3", t: "Carbonite (carb)：被忽略的「操作系统内核」", href: "chapters/01-stack/1-3-carbonite.html" },
            { id: "1-4", t: "USD Stage / Prim / Property 速成", href: "chapters/01-stack/1-4-usd-crash-course.html" },
          ],
        },
        {
          id: "2",
          num: "2",
          title: "RTX 渲染与 GAMES101 的鸿沟",
          sections: [
            { id: "2-1", t: "Rasterization vs RayTracing vs PathTracing", href: "chapters/01-stack/2-1-raster-vs-rt.html" },
            { id: "2-2", t: "RTX hardware：从 Turing 到 Ampere", href: "chapters/01-stack/2-2-rtx-hardware.html" },
            { id: "2-3", t: "从 MVP 矩阵到 Isaac Sim Camera sensor", href: "chapters/01-stack/2-3-camera-evolution.html" },
            { id: "2-4", t: "HDR / DomeLight / Environment lighting", href: "chapters/01-stack/2-4-hdr-lighting.html" },
          ],
        },
      ],
    },
    {
      n: "II",
      title: "渲染管线核心 · Core Pipeline",
      chapters: [
        {
          id: "3",
          num: "3",
          title: "数据流与模块架构",
          sections: [
            { id: "3-1", t: "六步数据流总览", href: "chapters/02-core/3-1-data-flow.html" },
            { id: "3-2", t: "Scene 模块：World、Stage、HDRI", href: "chapters/02-core/3-2-scene-module.html" },
            { id: "3-3", t: "Camera 模块：Spherical Look-At", href: "chapters/02-core/3-3-camera-module.html" },
            { id: "3-4", t: "Renderer 模块：Orchestration", href: "chapters/02-core/3-4-renderer-module.html" },
            { id: "3-5", t: "Alpha 合成：白色物体生存指南", href: "chapters/02-core/3-5-alpha-compositing.html" },
          ],
        },
        {
          id: "4",
          num: "4",
          title: "相机系统深度解析",
          sections: [
            { id: "4-1", t: "Bounding Box 驱动的相机距离", href: "chapters/02-core/4-1-bbox-camera.html" },
            { id: "4-2", t: "Azimuth / Elevation / Distance 交互演示", href: "chapters/02-core/4-2-spherical-widget.html" },
            { id: "4-3", t: "Sensor Annotators：RGBA、Depth、BBox2D", href: "chapters/02-core/4-3-annotators.html" },
            { id: "4-4", t: "View 命名约定：front / left / back / right", href: "chapters/02-core/4-4-view-naming.html" },
          ],
        },
      ],
    },
    {
      n: "III",
      title: "生产级健壮性 · Production Robustness",
      chapters: [
        {
          id: "5",
          num: "5",
          title: "Bounding Box 攻防战",
          sections: [
            { id: "5-1", t: "Authored extent vs mesh points：两条路线的较量", href: "chapters/03-robustness/5-1-bbox-strategies.html" },
            { id: "5-2", t: "Center-offset 陷阱与 fallback 策略", href: "chapters/03-robustness/5-2-center-offset.html" },
            { id: "5-3", t: "NaN / Inf 检查：数值稳定的最后一道防线", href: "chapters/03-robustness/5-3-nan-inf.html" },
          ],
        },
        {
          id: "6",
          num: "6",
          title: "Crash 与内存：工程智慧",
          sections: [
            { id: "6-1", t: "Camera Distance Bug：一条 np.clip 引发的血案", href: "chapters/03-robustness/6-1-camera-distance-bug.html" },
            { id: "6-2", t: "Segmentation Fault 全复盘：DLC Crash Fix", href: "chapters/03-robustness/6-2-dlc-crash.html" },
            { id: "6-3", t: "GPU 资源清理：cleanup() 方法论", href: "chapters/03-robustness/6-3-cleanup.html" },
            { id: "6-4", t: "world.reset() 与渲染步数的玄学", href: "chapters/03-robustness/6-4-world-reset.html" },
          ],
        },
      ],
    },
    {
      n: "IV",
      title: "规模化渲染 · Scale",
      chapters: [
        {
          id: "7",
          num: "7",
          title: "CLI 与批量渲染",
          sections: [
            { id: "7-1", t: "从单文件到批量：CLI 设计哲学", href: "chapters/04-scale/7-1-cli-design.html" },
            { id: "7-2", t: "Chunking：DLC 分布式渲染策略", href: "chapters/04-scale/7-2-chunking.html" },
            { id: "7-3", t: "MDL 材质路径修复与材质系统", href: "chapters/04-scale/7-3-mdl-fix.html" },
          ],
        },
      ],
    },
    {
      n: "V",
      title: "综合 · Capstone",
      chapters: [
        {
          id: "8",
          num: "8",
          title: "端到端与思维模型",
          sections: [
            { id: "8-1", t: "跑通一次完整渲染", href: "chapters/05-capstone/8-1-run-pipeline.html" },
            { id: "8-2", t: "Mental Model：一张图理解全管线", href: "chapters/05-capstone/8-2-mental-model.html" },
            { id: "8-3", t: "如何调试、扩展与贡献", href: "chapters/05-capstone/8-3-debug-extend.html" },
          ],
        },
        {
          id: "app",
          num: "App",
          title: "附录 · Appendix",
          sections: [
            { id: "app-glossary", t: "Glossary 中英术语表", href: "chapters/appendix/glossary.html" },
            { id: "app-cli", t: "CLI Cheat-sheet", href: "chapters/appendix/cli-cheatsheet.html" },
            { id: "app-bib", t: "Bibliography 参考资料", href: "chapters/appendix/bibliography.html" },
          ],
        },
      ],
    },
  ],
};

window.BOOK.flat = (function () {
  const out = [];
  window.BOOK.parts.forEach(function (part) {
    part.chapters.forEach(function (ch) {
      ch.sections.forEach(function (sec) {
        out.push({
          id: sec.id,
          t: sec.t,
          href: sec.href,
          chapter: ch.num,
          chapterTitle: ch.title,
          part: part.n,
          partTitle: part.title,
        });
      });
    });
  });
  return out;
})();
