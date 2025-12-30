module.exports = {
  parser: "@typescript-eslint/parser",
  extends: [
    "airbnb",
    "prettier",
    "plugin:react/recommended",
    "plugin:@typescript-eslint/recommended",
  ],
  plugins: ["prettier"],
  rules: {
    "arrow-body-style": ["error", "as-needed"],
    "class-methods-use-this": [1, { exceptMethods: ["render"] }],
    "jsx-a11y/label-has-associated-control": [
      "error",
      {
        labelComponents: [],
        labelAttributes: [],
        controlComponents: [],
        assert: "both",
        depth: 25,
      },
    ],
    "import/no-named-as-default": "off",
    "import/prefer-default-export": "off",
    "import/extensions": "off",

    "no-case-declarations": "off",
    "no-console": ["error", { allow: ["error"] }],
    "no-param-reassign": "off",
    "no-shadow": "off",
    "no-underscore-dangle": "off",
    "no-unneeded-ternary": "off",
    "no-use-before-define": "off", // Defined in airbnb

    "prettier/prettier": "error",

    "react/forbid-prop-types": "off",
    "react/jsx-filename-extension": "off",
    "react/jsx-one-expression-per-line": "off",
    "react/prefer-stateless-function": "off",
    "react/state-in-constructor": "off",
    "react/static-property-placement": "off",
    "react/destructuring-assignment": "off", // Defined in airbnb
    "react/require-default-props": "off", // Defined in airbnb
    "react/jsx-props-no-spreading": "off", // Defined in airbnb

    "no-unused-vars": "off",
    "@typescript-eslint/no-unused-vars": "off",
  },
  env: {
    es6: true,
    jest: true,
    browser: true,
  },
  parserOptions: {
    ecmaFeatures: {
      jsx: true,
      globalReturn: false,
    },
    ecmaVersion: 2020,
    project: ["tsconfig.json"],
    sourceType: "module",
  },
  settings: {
    react: {
      version: "detect",
    },
    "import/resolver": {
      typescript: {},
    },
  },
};
