In this plan you write each test's body when the tool switches it on, before the code that makes it pass.

The body checks what the test's docstring says, through the owner its mark names, using the real interface. Assert what the example states and leave other details open, so a different correct implementation would also pass. Run the test and see it fail on its assertion, with imports and collection working, before you write the code.

For a test marked `change`, rewrite the existing body to the new docstring. A `protect` test whose owner is in your task has no body yet either: write it before your first step and see it pass against the code as it stands.
