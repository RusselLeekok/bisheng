type BrandConfig = {
    brandName?: { zh?: string; en?: string; ja?: string };
    linsightAgentName?: { zh?: string; en?: string; ja?: string };
    linsightFullName?: { zh?: string; en?: string; ja?: string };
    loadingIcon?: string;
    loadingAnimation?: string;
    logos?: {
        favicon?: string;
        header?: string;
        loginSmall?: string;
        loginSmallDark?: string;
        loginBig?: string;
        loginDark?: string;
        officeLogo?: string;
        appStartLogo?: string;
    };
    links?: {
        github?: string;
        docs?: string;
        showGithub?; boolean;
        showDocs?: boolean;
    };
    version?: {
        show?: boolean;
        prefix?: string;
        label?: string;
    };
    text?: {
        watermark?: string;
        docTitle?: string;
    };
};

const cfg: BrandConfig = window.BRAND_CONFIG || {};
const baseUrl = __APP_ENV__?.BASE_URL || "";

const withBase = (path?: string) => {
    if (!path) return "";
    if (path.startsWith("http://") || path.startsWith("https://")) return path;
    return `${baseUrl}${path}`;
};

export const brand = {
    brandName: cfg.brandName || { zh: "BISHENG", en: "BISHENG", ja: "BISHENG" },
    linsightAgentName: cfg.linsightAgentName || { zh: "灵思", en: "Linsight", ja: "Linsight" },
    linsightFullName: cfg.linsightFullName || { zh: "灵思Linsight", en: "Linsight", ja: "Linsight" },
    loadingIcon: withBase(cfg.loadingIcon || ""),
    loadingAnimation: cfg.loadingAnimation || "",
    logos: {
        favicon: withBase(cfg.logos?.favicon || "/assets/bisheng/favicon.ico"),
        header: withBase(cfg.logos?.header || "/assets/bisheng/login-logo-small.png"),
        loginSmall: withBase(cfg.logos?.loginSmall || "/assets/bisheng/login-logo-small.png"),
        loginSmallDark: withBase(cfg.logos?.loginSmallDark || "/assets/bisheng/logo-small-dark.png"),
        loginBig: withBase(cfg.logos?.loginBig || "/assets/bisheng/login-logo-big.png"),
        loginDark: withBase(cfg.logos?.loginDark || "/assets/bisheng/login-logo-dark.png"),
        officeLogo: withBase(cfg.logos?.officeLogo || "/assets/bisheng/logo.jpeg"),
        appStartLogo: withBase(cfg.logos?.appStartLogo || "/assets/application-start-logo.png")
    },
    links: {
        github: cfg.links?.github || "https://github.com/dataelement/bisheng",
        docs: cfg.links?.docs || "https://m7a7tqsztt.feishu.cn/wiki/ZxW6wZyAJicX4WkG0NqcWsbynde",
        showGithub: cfg.links?.showGithub ?? true,
        showDocs: cfg.links?.showDocs ?? true
    },
    version: {
        show: cfg.version?.show ?? true,
        prefix: cfg.version?.prefix ?? "v",
        label: cfg.version?.label ?? ""
    },
    text: {
        watermark: cfg.text?.watermark || "BISHENG",
        docTitle: cfg.text?.docTitle || "bisheng.docx"
    }
};