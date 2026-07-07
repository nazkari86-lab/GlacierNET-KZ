#include "glacierkz/band_math.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <sstream>

namespace glacierkz {

Token::Token(TokenType type, std::string value)
    : type(type), value(std::move(value)) {}

ExpressionLexer::ExpressionLexer(const std::string& expr)
    : input_(expr), pos_(0) {}

std::vector<Token> ExpressionLexer::tokenize() {
    std::vector<Token> tokens;
    skip_whitespace();
    while (pos_ < input_.size()) {
        char c = input_[pos_];
        if (std::isdigit(c) || c == '.') {
            tokens.push_back(read_number());
        } else if (std::isalpha(c) || c == '_') {
            tokens.push_back(read_identifier());
        } else if (c == '+' || c == '-' || c == '*' || c == '/' ||
                   c == '(' || c == ')' || c == ',') {
            tokens.push_back(Token(TokenType::Operator, std::string(1, c)));
            pos_++;
        } else if (c == '>' || c == '<' || c == '!' || c == '=' || c == '&') {
            tokens.push_back(read_comparison());
        } else {
            throw std::runtime_error("Unexpected character: " + std::string(1, c));
        }
        skip_whitespace();
    }
    tokens.push_back(Token(TokenType::End, ""));
    return tokens;
}

void ExpressionLexer::skip_whitespace() {
    while (pos_ < input_.size() && std::isspace(input_[pos_])) {
        pos_++;
    }
}

Token ExpressionLexer::read_number() {
    size_t start = pos_;
    bool has_dot = false;
    while (pos_ < input_.size() &&
           (std::isdigit(input_[pos_]) || input_[pos_] == '.')) {
        if (input_[pos_] == '.') {
            if (has_dot) break;
            has_dot = true;
        }
        pos_++;
    }
    return Token(TokenType::Number, input_.substr(start, pos_ - start));
}

Token ExpressionLexer::read_identifier() {
    size_t start = pos_;
    while (pos_ < input_.size() &&
           (std::isalnum(input_[pos_]) || input_[pos_] == '_')) {
        pos_++;
    }
    std::string name = input_.substr(start, pos_ - start);
    if (is_function(name)) {
        return Token(TokenType::Function, name);
    }
    return Token(TokenType::Identifier, name);
}

Token ExpressionLexer::read_comparison() {
    size_t start = pos_;
    char c = input_[pos_++];
    if (pos_ < input_.size() && input_[pos_] == '=') {
        pos_++;
        if (c == '>' || c == '<' || c == '!' || c == '=') {
            return Token(TokenType::Operator,
                         std::string(1, c) + "=");
        }
    }
    if (c == '&' && pos_ < input_.size() && input_[pos_] == '&') {
        pos_++;
        return Token(TokenType::Operator, "&&");
    }
    return Token(TokenType::Operator, std::string(1, c));
}

bool ExpressionLexer::is_function(const std::string& name) {
    static const std::vector<std::string> fns = {
        "sqrt", "pow", "log", "exp", "sin", "cos", "tan",
        "abs", "max", "min", "clip", "where", "nan_to_num",
        "isnan", "isinf"
    };
    return std::find(fns.begin(), fns.end(), name) != fns.end();
}

ExpressionParser::ExpressionParser(const std::vector<Token>& tokens)
    : tokens_(tokens), pos_(0) {}

std::shared_ptr<ExprNode> ExpressionParser::parse() {
    auto node = parse_expression();
    if (pos_ < tokens_.size() && tokens_[pos_].type != TokenType::End) {
        throw std::runtime_error("Unexpected token: " + tokens_[pos_].value);
    }
    return node;
}

std::shared_ptr<ExprNode> ExpressionParser::parse_expression() {
    auto left = parse_comparison();
    while (pos_ < tokens_.size() && tokens_[pos_].type == TokenType::Operator &&
           (tokens_[pos_].value == "&&" || tokens_[pos_].value == "||")) {
        std::string op = tokens_[pos_].value;
        pos_++;
        auto right = parse_comparison();
        left = std::make_shared<BinaryOpNode>(op, std::move(left), std::move(right));
    }
    return left;
}

std::shared_ptr<ExprNode> ExpressionParser::parse_comparison() {
    auto left = parse_add_sub();
    while (pos_ < tokens_.size() && tokens_[pos_].type == TokenType::Operator &&
           (tokens_[pos_].value == "<" || tokens_[pos_].value == ">" ||
            tokens_[pos_].value == "<=" || tokens_[pos_].value == ">=" ||
            tokens_[pos_].value == "==" || tokens_[pos_].value == "!=")) {
        std::string op = tokens_[pos_].value;
        pos_++;
        auto right = parse_add_sub();
        left = std::make_shared<BinaryOpNode>(op, std::move(left), std::move(right));
    }
    return left;
}

std::shared_ptr<ExprNode> ExpressionParser::parse_add_sub() {
    auto left = parse_mul_div();
    while (pos_ < tokens_.size() && tokens_[pos_].type == TokenType::Operator &&
           (tokens_[pos_].value == "+" || tokens_[pos_].value == "-")) {
        std::string op = tokens_[pos_].value;
        pos_++;
        auto right = parse_mul_div();
        left = std::make_shared<BinaryOpNode>(op, std::move(left), std::move(right));
    }
    return left;
}

std::shared_ptr<ExprNode> ExpressionParser::parse_mul_div() {
    auto left = parse_unary();
    while (pos_ < tokens_.size() && tokens_[pos_].type == TokenType::Operator &&
           (tokens_[pos_].value == "*" || tokens_[pos_].value == "/")) {
        std::string op = tokens_[pos_].value;
        pos_++;
        auto right = parse_unary();
        left = std::make_shared<BinaryOpNode>(op, std::move(left), std::move(right));
    }
    return left;
}

std::shared_ptr<ExprNode> ExpressionParser::parse_unary() {
    if (pos_ < tokens_.size() && tokens_[pos_].type == TokenType::Operator) {
        if (tokens_[pos_].value == "-") {
            pos_++;
            auto operand = parse_primary();
            return std::make_shared<UnaryOpNode>("-", std::move(operand));
        } else if (tokens_[pos_].value == "!") {
            pos_++;
            auto operand = parse_primary();
            return std::make_shared<UnaryOpNode>("!", std::move(operand));
        }
    }
    return parse_primary();
}

std::shared_ptr<ExprNode> ExpressionParser::parse_primary() {
    if (pos_ >= tokens_.size()) {
        throw std::runtime_error("Unexpected end of expression");
    }

    const Token& tok = tokens_[pos_];

    if (tok.type == TokenType::Number) {
        pos_++;
        return std::make_shared<NumberNode>(std::stof(tok.value));
    }

    if (tok.type == TokenType::Identifier) {
        pos_++;
        return std::make_shared<VariableNode>(tok.value);
    }

    if (tok.type == TokenType::Function) {
        std::string fname = tok.value;
        pos_++;
        if (pos_ < tokens_.size() && tokens_[pos_].value == "(") {
            pos_++;
            std::vector<std::shared_ptr<ExprNode>> args;
            if (pos_ < tokens_.size() && tokens_[pos_].value != ")") {
                args.push_back(parse_expression());
                while (pos_ < tokens_.size() && tokens_[pos_].value == ",") {
                    pos_++;
                    args.push_back(parse_expression());
                }
            }
            if (pos_ < tokens_.size()) pos_++;
            return std::make_shared<FunctionNode>(fname, std::move(args));
        }
        return std::make_shared<FunctionNode>(fname, std::vector<std::shared_ptr<ExprNode>>{});
    }

    if (tok.type == TokenType::Operator && tok.value == "(") {
        pos_++;
        auto expr = parse_expression();
        if (pos_ < tokens_.size() && tokens_[pos_].value == ")") {
            pos_++;
        }
        return expr;
    }

    throw std::runtime_error("Unexpected token: " + tok.value);
}

std::vector<std::string> ExpressionParser::find_variable_names() {
    std::vector<std::string> names;
    for (const auto& tok : tokens_) {
        if (tok.type == TokenType::Identifier) {
            if (std::find(names.begin(), names.end(), tok.value) == names.end()) {
                names.push_back(tok.value);
            }
        }
    }
    return names;
}

float ExpressionEvaluator::evaluate(const ExprNode& node,
                                     const std::unordered_map<std::string, float>& vars) const {
    if (auto* num = dynamic_cast<const NumberNode*>(&node)) {
        return num->value;
    }

    if (auto* var = dynamic_cast<const VariableNode*>(&node)) {
        auto it = vars.find(var->name);
        if (it == vars.end()) {
            throw std::runtime_error("Unknown variable: " + var->name);
        }
        return it->second;
    }

    if (auto* bin = dynamic_cast<const BinaryOpNode*>(&node)) {
        float left = evaluate(*bin->left, vars);
        float right = evaluate(*bin->right, vars);

        if (bin->op == "+") return left + right;
        if (bin->op == "-") return left - right;
        if (bin->op == "*") return left * right;
        if (bin->op == "/") {
            if (std::abs(right) < 1e-10f) return 0.0f;
            return left / right;
        }
        if (bin->op == "<") return left < right ? 1.0f : 0.0f;
        if (bin->op == ">") return left > right ? 1.0f : 0.0f;
        if (bin->op == "<=") return left <= right ? 1.0f : 0.0f;
        if (bin->op == ">=") return left >= right ? 1.0f : 0.0f;
        if (bin->op == "==") return (std::abs(left - right) < 1e-10f) ? 1.0f : 0.0f;
        if (bin->op == "!=") return (std::abs(left - right) >= 1e-10f) ? 1.0f : 0.0f;
        if (bin->op == "&&") return (left != 0.0f && right != 0.0f) ? 1.0f : 0.0f;
        if (bin->op == "||") return (left != 0.0f || right != 0.0f) ? 1.0f : 0.0f;

        throw std::runtime_error("Unknown operator: " + bin->op);
    }

    if (auto* unary = dynamic_cast<const UnaryOpNode*>(&node)) {
        float operand = evaluate(*unary->operand, vars);
        if (unary->op == "-") return -operand;
        if (unary->op == "!") return (operand == 0.0f) ? 1.0f : 0.0f;
        throw std::runtime_error("Unknown unary operator: " + unary->op);
    }

    if (auto* func = dynamic_cast<const FunctionNode*>(&node)) {
        return evaluate_function(func->name, func->args, vars);
    }

    throw std::runtime_error("Unknown node type");
}

float ExpressionEvaluator::evaluate_function(
    const std::string& name,
    const std::vector<std::shared_ptr<ExprNode>>& args,
    const std::unordered_map<std::string, float>& vars) const {

    if (name == "sqrt") {
        return std::sqrt(evaluate(*args[0], vars));
    }
    if (name == "pow") {
        return std::pow(evaluate(*args[0], vars), evaluate(*args[1], vars));
    }
    if (name == "log") {
        float val = evaluate(*args[0], vars);
        return (val > 0.0f) ? std::log(val) : 0.0f;
    }
    if (name == "exp") {
        return std::exp(evaluate(*args[0], vars));
    }
    if (name == "sin") {
        return std::sin(evaluate(*args[0], vars));
    }
    if (name == "cos") {
        return std::cos(evaluate(*args[0], vars));
    }
    if (name == "tan") {
        return std::tan(evaluate(*args[0], vars));
    }
    if (name == "abs") {
        return std::abs(evaluate(*args[0], vars));
    }
    if (name == "max") {
        return std::max(evaluate(*args[0], vars), evaluate(*args[1], vars));
    }
    if (name == "min") {
        return std::min(evaluate(*args[0], vars), evaluate(*args[1], vars));
    }
    if (name == "clip") {
        float val = evaluate(*args[0], vars);
        float lo = evaluate(*args[1], vars);
        float hi = evaluate(*args[2], vars);
        return std::max(lo, std::min(hi, val));
    }
    if (name == "where") {
        float cond = evaluate(*args[0], vars);
        float if_true = evaluate(*args[1], vars);
        float if_false = evaluate(*args[2], vars);
        return (cond != 0.0f) ? if_true : if_false;
    }
    if (name == "nan_to_num") {
        float val = evaluate(*args[0], vars);
        return std::isnan(val) ? 0.0f : val;
    }
    if (name == "isnan") {
        return std::isnan(evaluate(*args[0], vars)) ? 1.0f : 0.0f;
    }
    if (name == "isinf") {
        return std::isinf(evaluate(*args[0], vars)) ? 1.0f : 0.0f;
    }

    throw std::runtime_error("Unknown function: " + name);
}

float ExpressionEvaluator::evaluate_single(const ExprNode& node,
                                            const std::unordered_map<std::string, float>& vars) const {
    return evaluate(node, vars);
}

BandMathEngine::BandMathEngine(
    const std::unordered_map<std::string, const float*>& band_data,
    size_t pixel_count)
    : band_data_(band_data), pixel_count_(pixel_count) {}

std::vector<float> BandMathEngine::compute(const std::string& expression) {
    ExpressionLexer lexer(expression);
    auto tokens = lexer.tokenize();

    ExpressionParser parser(tokens);
    auto ast = parser.parse();

    auto var_names = parser.find_variable_names();
    ExpressionEvaluator evaluator;

    std::vector<float> result(pixel_count_);
    std::unordered_map<std::string, float> vars;

    for (size_t i = 0; i < pixel_count_; ++i) {
        for (const auto& name : var_names) {
            auto it = band_data_.find(name);
            if (it != band_data_.end()) {
                vars[name] = it->second[i];
            }
        }
        result[i] = evaluator.evaluate(*ast, vars);
    }

    return result;
}

std::vector<float> BandMathEngine::compute_custom(
    const std::string& expression,
    const std::unordered_map<std::string, std::vector<float>>& extra_vars) {
    ExpressionLexer lexer(expression);
    auto tokens = lexer.tokenize();

    ExpressionParser parser(tokens);
    auto ast = parser.parse();

    auto var_names = parser.find_variable_names();
    ExpressionEvaluator evaluator;

    std::vector<float> result(pixel_count_);
    std::unordered_map<std::string, float> vars;

    for (size_t i = 0; i < pixel_count_; ++i) {
        for (const auto& name : var_names) {
            auto it = band_data_.find(name);
            if (it != band_data_.end()) {
                vars[name] = it->second[i];
            } else {
                auto eit = extra_vars.find(name);
                if (eit != extra_vars.end() && i < eit->second.size()) {
                    vars[name] = eit->second[i];
                }
            }
        }
        result[i] = evaluator.evaluate(*ast, vars);
    }

    return result;
}

void BandMathEngine::add_band(const std::string& name, const float* data) {
    band_data_[name] = data;
}

std::vector<std::string> BandMathEngine::list_bands() const {
    std::vector<std::string> names;
    names.reserve(band_data_.size());
    for (const auto& [name, _] : band_data_) {
        names.push_back(name);
    }
    return names;
}

} // namespace glacierkz
