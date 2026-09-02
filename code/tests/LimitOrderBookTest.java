import java.util.List;

/** Standalone tests; run with {@code java -ea LimitOrderBookTest}. */
public final class LimitOrderBookTest {

    public static void main(String[] args) {
        matchCrossesAtTheRestingOrderPrice();
        buyUsesLowestAskFirst();
        sellUsesHighestBidFirst();
        preservesFifoWithinPriceLevel();
        incomingOrderCanProduceMultipleFills();
        incomingRemainderRestsAndFillsLater();
        nonCrossingOrdersProduceNoFills();
        fillSnapshotsAreImmutable();
        System.out.println("LIMIT_ORDER_BOOK_TESTS_PASS");
    }

    private static void matchCrossesAtTheRestingOrderPrice() {
        LimitOrderBook book = new LimitOrderBook();
        book.match(order("b1", LimitOrderBook.Side.BUY, 100, 5));
        book.match(order("s1", LimitOrderBook.Side.SELL, 90, 2));

        assertFills(book, new LimitOrderBook.Fill("s1", 100, 2));
    }

    private static void buyUsesLowestAskFirst() {
        LimitOrderBook book = new LimitOrderBook();
        book.match(order("s1", LimitOrderBook.Side.SELL, 105, 2));
        book.match(order("s2", LimitOrderBook.Side.SELL, 103, 1));
        book.match(order("b1", LimitOrderBook.Side.BUY, 106, 3));

        assertFills(
            book,
            new LimitOrderBook.Fill("b1", 103, 1),
            new LimitOrderBook.Fill("b1", 105, 2)
        );
    }

    private static void sellUsesHighestBidFirst() {
        LimitOrderBook book = new LimitOrderBook();
        book.match(order("b1", LimitOrderBook.Side.BUY, 101, 2));
        book.match(order("b2", LimitOrderBook.Side.BUY, 103, 1));
        book.match(order("s1", LimitOrderBook.Side.SELL, 100, 3));

        assertFills(
            book,
            new LimitOrderBook.Fill("s1", 103, 1),
            new LimitOrderBook.Fill("s1", 101, 2)
        );
    }

    private static void preservesFifoWithinPriceLevel() {
        LimitOrderBook book = new LimitOrderBook();
        book.match(order("b1", LimitOrderBook.Side.BUY, 100, 2));
        book.match(order("b2", LimitOrderBook.Side.BUY, 100, 3));
        book.match(order("s1", LimitOrderBook.Side.SELL, 100, 4));

        assertFills(
            book,
            new LimitOrderBook.Fill("s1", 100, 2),
            new LimitOrderBook.Fill("s1", 100, 2)
        );
    }

    private static void incomingOrderCanProduceMultipleFills() {
        LimitOrderBook book = new LimitOrderBook();
        book.match(order("s1", LimitOrderBook.Side.SELL, 99, 1));
        book.match(order("s2", LimitOrderBook.Side.SELL, 100, 2));
        book.match(order("b1", LimitOrderBook.Side.BUY, 101, 5));

        assertFills(
            book,
            new LimitOrderBook.Fill("b1", 99, 1),
            new LimitOrderBook.Fill("b1", 100, 2)
        );
    }

    private static void incomingRemainderRestsAndFillsLater() {
        LimitOrderBook book = new LimitOrderBook();
        book.match(order("s1", LimitOrderBook.Side.SELL, 100, 5));
        book.match(order("b1", LimitOrderBook.Side.BUY, 100, 2));
        book.match(order("b2", LimitOrderBook.Side.BUY, 100, 3));

        assertFills(
            book,
            new LimitOrderBook.Fill("b1", 100, 2),
            new LimitOrderBook.Fill("b2", 100, 3)
        );
    }

    private static void nonCrossingOrdersProduceNoFills() {
        LimitOrderBook book = new LimitOrderBook();
        book.match(order("b1", LimitOrderBook.Side.BUY, 99, 7));
        book.match(order("s1", LimitOrderBook.Side.SELL, 100, 7));

        assertFills(book);
    }

    private static void fillSnapshotsAreImmutable() {
        LimitOrderBook book = new LimitOrderBook();
        book.match(order("s1", LimitOrderBook.Side.SELL, 100, 1));
        book.match(order("b1", LimitOrderBook.Side.BUY, 100, 1));

        List<LimitOrderBook.Fill> snapshot = book.getFills();
        if (!snapshot.equals(List.of(new LimitOrderBook.Fill("b1", 100, 1)))) {
            throw new AssertionError("unexpected fill snapshot: " + snapshot);
        }
        try {
            snapshot.clear();
            throw new AssertionError("fill snapshot must be immutable");
        } catch (UnsupportedOperationException expected) {
            // Expected: callers cannot mutate retained history.
        }
    }

    private static LimitOrderBook.Order order(
        String id,
        LimitOrderBook.Side side,
        long price,
        long quantity
    ) {
        return new LimitOrderBook.Order(id, side, price, quantity);
    }

    private static void assertFills(LimitOrderBook book, LimitOrderBook.Fill... expected) {
        List<LimitOrderBook.Fill> expectedFills = List.of(expected);
        if (!book.getFills().equals(expectedFills)) {
            throw new AssertionError(
                "expected fills " + expectedFills + " but got " + book.getFills()
            );
        }
    }
}
