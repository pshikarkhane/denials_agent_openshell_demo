// Hermes adapter: stub. See README.md in this folder.

/** @typedef {import('../types').RunSource} RunSource */

/** @type {RunSource} */
export const hermes = {
  kind: 'hermes',
  canRead() {
    return false;
  },
  read() {
    throw new Error('hermes adapter: not implemented yet');
  },
};
