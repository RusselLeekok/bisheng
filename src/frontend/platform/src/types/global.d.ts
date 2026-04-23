export { };

declare global {
    interface Window {
        SearchSkillsPage: any;
        errorAlerts: (errorList: string[]) => void;
        _flow: any;
        BRAND_CONFIG?: {
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
    }
}

declare module "*.png" {
    const content: any;
    export default content;
}


declare module "*.svg" {
    const content: any;
    export default content;
}
