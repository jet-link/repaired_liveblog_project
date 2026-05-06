import * as EditorJS from '@editorjs/editorjs';
declare type Props = {
    /**
     * Object that defines rules for automatic sanitizing.
     * @see https://editorjs.io/tools-api#sanitize
     * @default undefined
     */
    sanitize?: {};
    /**
     * [Shortcut](https://github.com/codex-team/codex.shortcuts) to apply
     * [Tool's render and inserting behaviour](https://editorjs.io/tools-api#shortcut)
     * @default undefined
     */
    shortcut?: string;
    /**
     * text [formatting tag](https://www.w3schools.com/html/html_formatting.asp)
     * (eg. `bold`)
     * @default undefined
     */
    tagName: string;
    /**
     * Icon for the tools [inline toolbar](https://editorjs.io/inline-tools-api-1#render)
     * @default undefined
     */
    toolboxIcon: string;
};
/**
 * GenericInlineTool returns an EditorJS.InlineTool capable of wrapping a
 * selected text with any given `tagName`.
 *
 * inspired by
 * @see https://github.com/editor-js/marker/blob/c306bcb33c88eaa3c172eaf387fbcd06ae6b297f/src/index.js
 */
declare const createGenericInlineTool: ({ sanitize, shortcut, tagName, toolboxIcon, }: Props) => {
    new ({ api }: {
        api: EditorJS.API;
    }): {
        api: EditorJS.API;
        button: HTMLButtonElement;
        tag: string;
        iconClasses: {
            active: string;
            base: string;
        };
        /**
         * Create button element for Toolbar
         *
         * @return {HTMLButtonElement}
         */
        render(): HTMLButtonElement;
        /**
         * Wrap/Unwrap selected fragment
         *
         * @param {Range} range - selected fragment
         */
        surround(range: Range): void;
        /**
         * Wrap selection with term-tag
         *
         * @param {Range} range - selected fragment
         */
        wrap(range: Range): void;
        /**
         * Unwrap term-tag
         *
         * @param {HTMLElement} termWrapper - term wrapper tag
         */
        unwrap(termWrapper: HTMLElement): void;
        /**
         * Check and change Term's state for current selection
         */
        checkState(): boolean;
        /**
         * Get Tool icon's SVG
         * @return {string}
         */
        readonly toolboxIcon: string;
        /**
         * Set a shortcut
         */
        readonly shortcut: string;
    };
    /**
     * Specifies Tool as Inline Toolbar Tool
     *
     * @return {boolean}
     */
    isInline: boolean;
    /**
     * Sanitizer rule
     * @return {Object.<string>} {Object.<string>}
     */
    readonly sanitize: {};
};
export default createGenericInlineTool;
//# sourceMappingURL=tool.d.ts.map