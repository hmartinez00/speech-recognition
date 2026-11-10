chrome.commands.onCommand.addListener((command) => {
  if (command === 'start-recording') {
    chrome.windows.create({
      url: chrome.runtime.getURL('record.html'),
      type: 'popup',
      width: 420,
      height: 180,
      focused: true
    });
  }
});
