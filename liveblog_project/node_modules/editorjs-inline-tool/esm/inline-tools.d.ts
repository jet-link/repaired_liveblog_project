export declare const ItalicInlineTool: {
    new ({ api }: {
        api: import("@editorjs/editorjs").API;
    }): {
        api: import("@editorjs/editorjs").API;
        button: HTMLButtonElement;
        tag: string;
        iconClasses: {
            active: string;
            base: string;
        };
        render(): HTMLButtonElement;
        surround(range: Range): void;
        wrap(range: Range): void;
        unwrap(termWrapper: HTMLElement): void;
        checkState(): boolean;
        readonly toolboxIcon: string;
        readonly shortcut: string;
    };
    isInline: boolean;
    readonly sanitize: {};
};
export declare const StrongInlineTool: {
    new ({ api }: {
        api: import("@editorjs/editorjs").API;
    }): {
        api: import("@editorjs/editorjs").API;
        button: HTMLButtonElement;
        tag: string;
        iconClasses: {
            active: string;
            base: string;
        };
        render(): HTMLButtonElement;
        surround(range: Range): void;
        wrap(range: Range): void;
        unwrap(termWrapper: HTMLElement): void;
        checkState(): boolean;
        readonly toolboxIcon: string;
        readonly shortcut: string;
    };
    isInline: boolean;
    readonly sanitize: {};
};
export declare const UnderlineInlineTool: {
    new ({ api }: {
        api: import("@editorjs/editorjs").API;
    }): {
        api: import("@editorjs/editorjs").API;
        button: HTMLButtonElement;
        tag: string;
        iconClasses: {
            active: string;
            base: string;
        };
        render(): HTMLButtonElement;
        surround(range: Range): void;
        wrap(range: Range): void;
        unwrap(termWrapper: HTMLElement): void;
        checkState(): boolean;
        readonly toolboxIcon: string;
        readonly shortcut: string;
    };
    isInline: boolean;
    readonly sanitize: {};
};
//# sourceMappingURL=inline-tools.d.ts.map